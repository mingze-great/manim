"""manim 平台健康监控 —— 每天 09:15 检查生产站点。

- 09:15 一次：GET https://www.lazymedia.cn/health 和 /api/health
- 非 2xx / 超时 / DNS 错 → 🔴 报警到 manim监控 群
- 全部 2xx 且周一 → 🟢 一条心跳；其他日子静默
- 命令入口：/monitor now  在当前群立返最新一次探测结果
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

CHINA_TZ = timezone(timedelta(hours=8))

MONITOR_EMPLOYEE = "manim监控"

TARGETS = [
    ("https://www.lazymedia.cn/health", 10),
    ("https://www.lazymedia.cn/api/health", 10),
]


@dataclass
class Probe:
    url: str
    ok: bool
    status: int
    latency_ms: int
    error: str = ""


async def probe_one(client: httpx.AsyncClient, url: str, timeout: float) -> Probe:
    t0 = datetime.now()
    try:
        r = await client.get(url, timeout=timeout, follow_redirects=True,
                             headers={"User-Agent": "openclaw-monitor/1.0"})
        latency = int((datetime.now() - t0).total_seconds() * 1000)
        return Probe(url=url, ok=200 <= r.status_code < 300,
                     status=r.status_code, latency_ms=latency)
    except Exception as e:  # noqa: BLE001
        latency = int((datetime.now() - t0).total_seconds() * 1000)
        return Probe(url=url, ok=False, status=0, latency_ms=latency,
                     error=f"{type(e).__name__}: {e}")


async def probe_all() -> list[Probe]:
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(*[probe_one(client, u, t) for u, t in TARGETS])


def format_report(probes: list[Probe]) -> tuple[bool, str]:
    """返回 (整体是否 OK, 展示文本)"""
    all_ok = all(p.ok for p in probes)
    icon = "🟢" if all_ok else "🔴"
    lines = [f"{icon} manim 平台健康探测 · {datetime.now(CHINA_TZ).strftime('%Y-%m-%d %H:%M')}"]
    for p in probes:
        mark = "✅" if p.ok else "❌"
        detail = f"HTTP {p.status}" if p.status else p.error
        lines.append(f"{mark} {p.url}  {p.latency_ms}ms  {detail}")
    return all_ok, "\n".join(lines)


def _get_target_chat_id() -> Optional[str]:
    from app.openclaw.team import load_state
    emp = load_state().find(MONITOR_EMPLOYEE)
    return emp.chat_id if emp else None


async def push_result_if_needed() -> dict:
    """定时任务用：只在异常或周一时推送。"""
    probes = await probe_all()
    all_ok, text = format_report(probes)
    now = datetime.now(CHINA_TZ)
    should_send = (not all_ok) or (now.weekday() == 0)  # Monday
    result = {"ok": all_ok, "sent": False, "text": text}
    if not should_send:
        return result

    chat_id = _get_target_chat_id()
    if not chat_id:
        return result
    from app.openclaw.config import get_openclaw_settings
    from app.openclaw.feishu import FeishuClient
    fs = FeishuClient(get_openclaw_settings())
    ok = await fs.send_to_chat(chat_id, text)
    result["sent"] = ok
    return result


async def probe_and_render() -> str:
    """/monitor now 用：无论好坏都返回文本。"""
    probes = await probe_all()
    _, text = format_report(probes)
    return text


# ---- 命令入口（在 service._handle_command 里挂 "/monitor"）----

async def handle_command_monitor(chat_id: str, rest: str) -> list[str]:
    sub = (rest.strip().split() or ["now"])[0].lower()
    if sub == "now":
        text = await probe_and_render()
        return [text]
    return [
        "🔍 manim 监控用法：",
        "/monitor now   立刻探测一次并返回",
        "（每天 09:15 自动跑；异常或周一才推送）",
    ]


# ---- 调度 ----

_SCHED = None


def start_monitor_scheduler() -> None:
    global _SCHED
    if _SCHED is not None:
        return
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _SCHED = AsyncIOScheduler(timezone=CHINA_TZ)
    _SCHED.add_job(_run_safe, CronTrigger(hour=9, minute=15),
                   id="monitor_daily", replace_existing=True, misfire_grace_time=3600)
    _SCHED.start()
    print("[openclaw.monitor] scheduler started -- daily 09:15")


def shutdown_monitor_scheduler() -> None:
    global _SCHED
    if _SCHED is not None:
        _SCHED.shutdown(wait=False)
        _SCHED = None


async def _run_safe() -> None:
    try:
        result = await push_result_if_needed()
        print(f"[openclaw.monitor] daily result: ok={result['ok']} sent={result['sent']}")
    except Exception as e:  # noqa: BLE001
        print(f"[openclaw.monitor] daily 异常: {type(e).__name__}: {e}")
