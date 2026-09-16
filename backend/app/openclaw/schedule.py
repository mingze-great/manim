"""日程助手 —— 独立 SQLite + 定时推送 + 命令 + 自然语言解析。

数据文件：openclaw_schedule.db（与 openclaw_state.json 同目录，即 backend/）
表：schedules
  id INTEGER PK
  chat_id TEXT      推送时用的目标群（一般 = 日程助手群）
  user_open_id TEXT 谁创建的（可空）
  title TEXT
  remind_at TEXT    ISO 时间 (Asia/Shanghai，"YYYY-MM-DDTHH:MM")
  repeat TEXT       none / daily / weekdays / weekly
  notes TEXT
  done INT
  reminded INT      分钟扫描已推送标记（避免重复）
  created_at TEXT

命令入口在 service.py 的 _handle_command 里挂 "/schedule"。
"""
from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

CHINA_TZ = timezone(timedelta(hours=8))

DB_PATH = Path(__file__).resolve().parents[2] / "openclaw_schedule.db"

# ---- 员工名（花名册里 team.py 的 chat_id 决定推送目标群）----
SCHEDULE_EMPLOYEE = "日程助手"


# ---- SQLite ----

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            user_open_id TEXT,
            title TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            repeat TEXT DEFAULT 'none',
            notes TEXT DEFAULT '',
            done INTEGER DEFAULT 0,
            reminded INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


@dataclass
class Schedule:
    id: int
    chat_id: str
    user_open_id: str
    title: str
    remind_at: datetime  # tz-aware in China TZ
    repeat: str
    notes: str
    done: bool
    reminded: bool

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Schedule":
        dt = datetime.fromisoformat(row["remind_at"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CHINA_TZ)
        return cls(
            id=row["id"],
            chat_id=row["chat_id"] or "",
            user_open_id=row["user_open_id"] or "",
            title=row["title"],
            remind_at=dt,
            repeat=row["repeat"] or "none",
            notes=row["notes"] or "",
            done=bool(row["done"]),
            reminded=bool(row["reminded"]),
        )


def add_schedule(chat_id: str, title: str, remind_at: datetime,
                 repeat: str = "none", notes: str = "",
                 user_open_id: str = "") -> Schedule:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO schedules (chat_id, user_open_id, title, remind_at, repeat, notes, done, reminded, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)",
            (
                chat_id,
                user_open_id,
                title,
                remind_at.astimezone(CHINA_TZ).strftime("%Y-%m-%dT%H:%M"),
                repeat,
                notes,
                datetime.now(CHINA_TZ).isoformat(),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM schedules WHERE id = ?", (cur.lastrowid,)).fetchone()
        return Schedule.from_row(row)
    finally:
        conn.close()


def mark_done(sched_id: int) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("UPDATE schedules SET done = 1 WHERE id = ?", (sched_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_schedule(sched_id: int) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM schedules WHERE id = ?", (sched_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_by_day(d: date, chat_id: Optional[str] = None) -> list[Schedule]:
    conn = _connect()
    try:
        q = "SELECT * FROM schedules WHERE remind_at LIKE ? "
        args: list = [f"{d.isoformat()}%"]
        if chat_id:
            q += "AND chat_id = ? "
            args.append(chat_id)
        q += "ORDER BY remind_at ASC"
        rows = conn.execute(q, args).fetchall()
        return [Schedule.from_row(r) for r in rows]
    finally:
        conn.close()


def list_pending_now(now: datetime) -> list[Schedule]:
    """分钟级到期扫描：done=0 且 reminded=0 且 remind_at <= now。"""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE done = 0 AND reminded = 0 AND remind_at <= ? "
            "ORDER BY remind_at ASC LIMIT 20",
            (now.astimezone(CHINA_TZ).strftime("%Y-%m-%dT%H:%M"),),
        ).fetchall()
        return [Schedule.from_row(r) for r in rows]
    finally:
        conn.close()


def mark_reminded(sched_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("UPDATE schedules SET reminded = 1 WHERE id = ?", (sched_id,))
        conn.commit()
    finally:
        conn.close()


# ---- 命令解析 ----

_ADD_RE = re.compile(
    r"^\s*(?:(\d{4}-\d{2}-\d{2})\s+)?(\d{1,2}):(\d{2})\s+(.+?)\s*$"
)


def _parse_add(rest: str) -> Optional[tuple[datetime, str]]:
    """
    /schedule add HH:MM 事项       → 今天该时间
    /schedule add YYYY-MM-DD HH:MM 事项 → 指定日期
    如果时间已过（且没写日期），自动挪到明天。
    """
    m = _ADD_RE.match(rest)
    if not m:
        return None
    ymd, hh, mm, title = m.groups()
    now = datetime.now(CHINA_TZ)
    hour, minute = int(hh), int(mm)
    if hour > 23 or minute > 59:
        return None
    if ymd:
        y, mo, d = map(int, ymd.split("-"))
        dt = datetime(y, mo, d, hour, minute, tzinfo=CHINA_TZ)
    else:
        dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt <= now:
            dt = dt + timedelta(days=1)
    return dt, title.strip()


def handle_command_schedule(chat_id: str, rest: str) -> list[str]:
    """
    子命令：
      /schedule add ...
      /schedule list
      /schedule done <id>
      /schedule del <id>
      （无参数）帮助
    """
    tokens = rest.split(None, 1)
    if not tokens:
        return [
            "📅 日程助手用法：",
            "/schedule add HH:MM 事项           今天该时间提醒",
            "/schedule add YYYY-MM-DD HH:MM 事项 指定日期",
            "/schedule list                     查看今日全部",
            "/schedule done <id>                标记完成",
            "/schedule del <id>                 删除",
        ]

    sub = tokens[0].lower()
    args = tokens[1] if len(tokens) > 1 else ""

    if sub == "add":
        parsed = _parse_add(args)
        if parsed is None:
            return ["❌ 用法：/schedule add [YYYY-MM-DD] HH:MM 事项"]
        dt, title = parsed
        s = add_schedule(chat_id=chat_id, title=title, remind_at=dt)
        return [
            f"✅ 已加入日程 #{s.id}",
            f"⏰ {dt.strftime('%Y-%m-%d %H:%M')}",
            f"📌 {title}",
        ]

    if sub == "list":
        today = datetime.now(CHINA_TZ).date()
        rows = list_by_day(today, chat_id=chat_id)
        if not rows:
            return [f"📅 {today} 今日无日程"]
        lines = [f"📅 {today} 今日日程（{len(rows)} 项）"]
        for r in rows:
            mark = "✅" if r.done else "⏳"
            lines.append(f"#{r.id} {mark} {r.remind_at.strftime('%H:%M')} {r.title}")
        return ["\n".join(lines)]

    if sub == "done":
        try:
            sid = int(args.strip().split()[0])
        except (ValueError, IndexError):
            return ["❌ 用法：/schedule done <id>"]
        ok = mark_done(sid)
        return [f"✅ 已完成 #{sid}" if ok else f"❌ 找不到 #{sid}"]

    if sub == "del":
        try:
            sid = int(args.strip().split()[0])
        except (ValueError, IndexError):
            return ["❌ 用法：/schedule del <id>"]
        ok = delete_schedule(sid)
        return [f"🗑 已删除 #{sid}" if ok else f"❌ 找不到 #{sid}"]

    return [f"未知子命令：{sub}"]


# ---- 自然语言解析（在日程群里）----

NL_PARSE_SYS = (
    "你是日程解析助手。用户会用中文说一件想被提醒的事，你要提取出：\n"
    "- action: 'add'（默认）| 'list' | 'done' | 'del' | 'none'\n"
    "- title:  一句话事项\n"
    "- remind_at: ISO 时间，Asia/Shanghai 时区，格式 YYYY-MM-DDTHH:MM\n"
    "- repeat: 'none' | 'daily' | 'weekdays' | 'weekly'\n"
    "解析规则：\n"
    "- 相对时间要换算成绝对时间（现在时间会给你）。\n"
    "- 如果用户只说了时间没说日期，且时间早于现在，自动挪到明天。\n"
    "- 如果内容不像日程（比如问答/闲聊），action 返回 'none'。\n"
    "严格只输出 JSON，不要任何多余文字："
    "{\"action\":\"add\",\"title\":\"…\",\"remind_at\":\"YYYY-MM-DDTHH:MM\",\"repeat\":\"none\"}"
)


async def parse_natural_language(text: str) -> Optional[dict]:
    """让 LLM 解析一句话为 schedule 结构；解析失败返回 None。"""
    from app.openclaw.config import get_openclaw_settings
    from app.openclaw.service import _call_chat_completions, get_effective_model

    cfg = get_openclaw_settings()
    model = get_effective_model(cfg, None)
    now = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M %A")
    messages = [
        {"role": "system", "content": NL_PARSE_SYS},
        {"role": "user", "content": f"当前时间：{now}\n用户说：{text}"},
    ]
    try:
        raw = await _call_chat_completions(cfg, messages, model)
    except Exception as e:  # noqa: BLE001
        print(f"[schedule.nl] LLM 失败: {e}")
        return None
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


async def handle_natural_language(chat_id: str, text: str) -> Optional[list[str]]:
    """尝试把自然语言当日程处理。返回 None 表示走原有链路。"""
    parsed = await parse_natural_language(text)
    if not parsed:
        return None
    action = (parsed.get("action") or "none").lower()
    if action == "none":
        return None
    if action == "add":
        title = (parsed.get("title") or "").strip()
        raw_dt = (parsed.get("remind_at") or "").strip()
        if not title or not raw_dt:
            return ["🤖 我理解成一条日程，但没抠出时间/事项，请再说一次或用 /schedule add"]
        try:
            dt = datetime.fromisoformat(raw_dt)
        except ValueError:
            return ["🤖 我解析的时间不对，请换个说法或用 /schedule add"]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CHINA_TZ)
        repeat = (parsed.get("repeat") or "none").lower()
        s = add_schedule(chat_id=chat_id, title=title, remind_at=dt, repeat=repeat)
        return [
            f"✅ 已加入日程 #{s.id}",
            f"⏰ {dt.astimezone(CHINA_TZ).strftime('%Y-%m-%d %H:%M')}",
            f"📌 {title}" + (f"（{repeat}）" if repeat != "none" else ""),
        ]
    if action == "list":
        return handle_command_schedule(chat_id, "list")
    return None


# ---- 定时推送 ----

_SCHED = None


def start_schedule_scheduler() -> None:
    global _SCHED
    if _SCHED is not None:
        return
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    _SCHED = AsyncIOScheduler(timezone=CHINA_TZ)
    _SCHED.add_job(_morning_push_safe, CronTrigger(hour=8, minute=30),
                   id="schedule_morning", replace_existing=True, misfire_grace_time=3600)
    _SCHED.add_job(_evening_push_safe, CronTrigger(hour=22, minute=0),
                   id="schedule_evening", replace_existing=True, misfire_grace_time=3600)
    _SCHED.add_job(_minute_scan_safe, IntervalTrigger(minutes=1),
                   id="schedule_minute_scan", replace_existing=True)
    _SCHED.start()
    print("[openclaw.schedule] scheduler started -- morning 08:30 / evening 22:00 / minute scan")


def shutdown_schedule_scheduler() -> None:
    global _SCHED
    if _SCHED is not None:
        _SCHED.shutdown(wait=False)
        _SCHED = None


async def _morning_push_safe() -> None:
    try:
        await _morning_push()
    except Exception as e:  # noqa: BLE001
        print(f"[schedule.morning] {type(e).__name__}: {e}")


async def _evening_push_safe() -> None:
    try:
        await _evening_push()
    except Exception as e:  # noqa: BLE001
        print(f"[schedule.evening] {type(e).__name__}: {e}")


async def _minute_scan_safe() -> None:
    try:
        await _minute_scan()
    except Exception as e:  # noqa: BLE001
        print(f"[schedule.scan] {type(e).__name__}: {e}")


def _get_target_chat_id() -> Optional[str]:
    from app.openclaw.team import load_state
    emp = load_state().find(SCHEDULE_EMPLOYEE)
    return emp.chat_id if emp else None


async def _morning_push() -> None:
    chat_id = _get_target_chat_id()
    if not chat_id:
        print("[schedule.morning] 花名册无日程助手，跳过")
        return
    today = datetime.now(CHINA_TZ).date()
    rows = list_by_day(today, chat_id=chat_id)
    if not rows:
        text = f"☀️ 早上好！{today} 今天没有安排的日程，加油！"
    else:
        lines = [f"☀️ 早上好！{today} 今日日程共 {len(rows)} 项"]
        for r in rows:
            mark = "✅" if r.done else "⏳"
            lines.append(f"  {mark} {r.remind_at.strftime('%H:%M')} #{r.id} {r.title}")
        text = "\n".join(lines)
    await _send(chat_id, text)


async def _evening_push() -> None:
    chat_id = _get_target_chat_id()
    if not chat_id:
        return
    today = datetime.now(CHINA_TZ).date()
    rows = list_by_day(today, chat_id=chat_id)
    tomorrow = today + timedelta(days=1)
    rows_tmr = list_by_day(tomorrow, chat_id=chat_id)

    parts = [f"🌙 晚安！{today} 完成情况"]
    if rows:
        done = sum(1 for r in rows if r.done)
        parts.append(f"  今日 {len(rows)} 项，完成 {done} 项。")
        for r in rows:
            mark = "✅" if r.done else "⏳"
            parts.append(f"  {mark} {r.remind_at.strftime('%H:%M')} #{r.id} {r.title}")
    else:
        parts.append("  今日无日程。")

    parts.append("")
    if rows_tmr:
        parts.append(f"📅 明日预告（{tomorrow} · {len(rows_tmr)} 项）")
        for r in rows_tmr:
            parts.append(f"  ⏳ {r.remind_at.strftime('%H:%M')} #{r.id} {r.title}")
    else:
        parts.append(f"📅 明日 {tomorrow} 暂无安排。")
    await _send(chat_id, "\n".join(parts))


async def _minute_scan() -> None:
    now = datetime.now(CHINA_TZ)
    pending = list_pending_now(now)
    for s in pending:
        target = s.chat_id or _get_target_chat_id()
        if not target:
            continue
        text = (f"🔔 到点提醒 #{s.id}\n"
                f"⏰ {s.remind_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"📌 {s.title}")
        ok = await _send(target, text)
        if ok:
            mark_reminded(s.id)


async def _send(chat_id: str, text: str) -> bool:
    from app.openclaw.config import get_openclaw_settings
    from app.openclaw.feishu import FeishuClient
    cfg = get_openclaw_settings()
    fs = FeishuClient(cfg)
    return await fs.send_to_chat(chat_id, text)


async def send_now(chat_id: str) -> None:
    """/schedule now — 立刻按 morning 格式推一次，用于测试。"""
    await _morning_push()  # 借用 morning 的格式；chat_id 参数留给未来定制
    _ = chat_id  # placeholder
    await asyncio.sleep(0)
