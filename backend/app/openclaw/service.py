"""业务逻辑：user_text -> boss 派单 / 命令 / 直答 -> 回复消息列表.

Boss 模式：
  - 主群（虾仁花旦所在的对话）里 —— 除命令外的普通消息都被视为「需求」，
    由 LLM 依据员工花名册选人 → 通过 FeishuClient 把任务发到对应员工群 →
    回复原会话「已派给 XX」。
  - 员工群（花名册里的 chat_id）里 —— 不做派单（避免自己派给自己），
    直接调 LLM 回答，方便 debug。

命令：
  /model                  查看/切换模型（多条消息，长按可复制单个名字）
  /team                   查看员工花名册
  /hire <name> <chat_id> <role...>   招新员工
  /fire <name>            解雇员工
  /help                   帮助
"""
import asyncio
import re
import time

import httpx

from app.openclaw.config import OpenClawSettings
from app.openclaw.feishu import FeishuClient
from app.openclaw.team import (
    build_dispatch_messages,
    fire,
    hire,
    load_state,
    parse_dispatch_json,
    CHAT_ID_RE,
)


FEISHU_TEXT_MAX = 4800

# ---- 会话级 model override ----
_CHAT_MODEL: dict[str, str] = {}

# ---- 上游模型列表缓存 ----
_MODELS_CACHE: dict[str, tuple[list[str], float]] = {}
_MODELS_TTL = 300


def get_effective_model(cfg: OpenClawSettings, chat_id: str | None) -> str:
    if chat_id and chat_id in _CHAT_MODEL:
        return _CHAT_MODEL[chat_id]
    return cfg.llm_model


def _normalized_base(cfg: OpenClawSettings) -> str:
    base = cfg.llm_base_url.rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    return base


async def list_upstream_models(cfg: OpenClawSettings) -> list[str]:
    base = _normalized_base(cfg)
    now = time.time()
    cached = _MODELS_CACHE.get(base)
    if cached and now - cached[1] < _MODELS_TTL:
        return cached[0]

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                base + "/models",
                headers={"Authorization": f"Bearer {cfg.llm_api_key}"},
            )
        data = resp.json()
        ids = sorted({m.get("id") for m in (data.get("data") or []) if m.get("id")})
    except Exception as e:  # noqa: BLE001
        print(f"[openclaw.service] list_upstream_models 失败: {type(e).__name__}: {e}")
        return []
    _MODELS_CACHE[base] = (ids, now)
    return ids


async def _call_chat_completions(
    cfg: OpenClawSettings, messages: list[dict], model: str
) -> str:
    if not cfg.llm_base_url or not cfg.llm_api_key:
        raise RuntimeError("OPENCLAW_LLM_BASE_URL / OPENCLAW_LLM_API_KEY 未配置")

    url = _normalized_base(cfg) + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": cfg.llm_temperature,
        "max_tokens": cfg.llm_max_tokens,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {cfg.llm_api_key}",
        "Content-Type": "application/json",
    }

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices") or []
                if not choices:
                    raise RuntimeError(f"empty choices: {str(data)[:400]}")
                msg = choices[0].get("message") or {}
                return msg.get("content") or ""
            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = RuntimeError(f"upstream {resp.status_code}: {resp.text[:200]}")
                print(f"[openclaw.service] attempt {attempt + 1} 短暂失败：{last_err}")
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"upstream {resp.status_code}: {resp.text[:400]}")
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_err = e
            print(f"[openclaw.service] attempt {attempt + 1} 网络异常：{type(e).__name__}: {e}")
            await asyncio.sleep(1.5 * (attempt + 1))
            continue

    raise RuntimeError(f"上游多次重试仍失败：{last_err}")


HELP_TEXT = (
    "🤖 虾仁花旦（Boss）— 我不亲自干活，我派活给员工。\n"
    "\n直接 @我 说需求即可（例如 '记一笔今天午饭 35'），我会自动派给合适的员工群。"
    "\n\n📋 命令：\n"
    "/team                          查看员工花名册\n"
    "/hire <name> <chat_id> <职责>  招新员工\n"
    "/fire <name>                   解雇员工\n"
    "/news now                      立即抓一次 AI 热点推送到 AI热点群\n"
    "/model                         查看/切换模型\n"
    "/help                          本帮助"
)


async def _run_news_and_ack(
    fs_client: FeishuClient | None,
    ack_chat_id: str | None,
    target_chat_id: str | None = None,
) -> None:
    """后台跑一次 AI 热点推送。
    target_chat_id 传了就发到该群；不传按默认（花名册里的 AI热点）。
    ack_chat_id 是触发命令的那个群，用来发状态回执；失败时才发提示。
    """
    try:
        from app.openclaw.news import push_daily
        result = await push_daily(chat_id=target_chat_id)
    except Exception as e:  # noqa: BLE001
        print(f"[openclaw.service] /news 触发失败: {type(e).__name__}: {e}")
        if fs_client and ack_chat_id:
            await fs_client.send_to_chat(ack_chat_id, f"❌ AI 热点抓取失败：{type(e).__name__}: {e}")
        return
    if not result.get("ok") and fs_client and ack_chat_id:
        await fs_client.send_to_chat(ack_chat_id, f"⚠️ AI 热点未推送：{result.get('error')}")
    # 成功且是发到当前群，不再发额外回执（日报本身就是回复）
    elif result.get("ok") and target_chat_id is None and fs_client and ack_chat_id:
        await fs_client.send_to_chat(
            ack_chat_id,
            f"✅ AI 热点已推送：{result['picked']} 条已发到 AI热点群",
        )


# ---- 命令 ----

async def _handle_command(
    text: str,
    cfg: OpenClawSettings,
    chat_id: str | None,
    fs_client: FeishuClient | None,
) -> list[str] | None:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    parts = stripped.split(None, 1)
    cmd = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/help", "/帮助"):
        return [HELP_TEXT]

    if cmd == "/team":
        state = load_state()
        emps = state.list_all()
        if not emps:
            return ["👥 团队暂无员工，用 /hire 添加"]
        msgs: list[str] = [f"👥 团队（{len(emps)} 人）— 长按可复制单条"]
        for e in emps:
            msgs.append(f"{e.name} · {e.chat_id}\n职责：{e.role}")
        return msgs

    if cmd == "/hire":
        # /hire <name> <chat_id> <role...>
        tokens = rest.split(None, 2)
        if len(tokens) < 3:
            return [
                "❌ 用法：/hire <name> <chat_id> <职责描述>",
                "例：/hire 采购 oc_xxxx 负责采买、比价、下单",
            ]
        name, cid, role = tokens[0], tokens[1], tokens[2]
        if not CHAT_ID_RE.match(cid):
            return [f"❌ chat_id 格式不对（应形如 oc_ 开头 32 位十六进制）：{cid}"]
        # 校验群可访问
        if fs_client is not None:
            info = await fs_client.chat_info(cid)
            if info is None:
                return [
                    f"❌ 无法访问 chat_id={cid}（bot 不在群里，或没权限）。",
                    "请先把「虾仁花旦」拉进那个群，或检查开发者后台的 App 权限。",
                ]
        e = hire(name, cid, role)
        return [
            f"✅ 已录用 {e.name}",
            f"chat_id：{e.chat_id}",
            f"职责：{e.role}",
            "以后你 @我 提相关需求，会自动派单过去。",
        ]

    if cmd == "/news":
        sub = rest.split()[0].lower() if rest else "now"
        if sub == "now":
            asyncio.create_task(_run_news_and_ack(fs_client, chat_id))
            return ["🚀 已开始抓取 AI 热点，抓完会推送到 AI热点群，稍等约 30~60 秒"]
        return ["用法：/news now  （立即触发一次 AI 热点推送）"]

    if cmd == "/fire":
        if not rest:
            return ["❌ 用法：/fire <name>"]
        name = rest.split()[0]
        ok = fire(name)
        return [f"✅ 已解雇 {name}" if ok else f"❌ 花名册里没找到 {name}"]

    if cmd == "/model":
        current = get_effective_model(cfg, chat_id)
        default = cfg.llm_model
        if not rest:
            models = await list_upstream_models(cfg)
            msgs: list[str] = [f"当前模型：{current}（默认 {default}）"]
            if models:
                msgs.append("👇 长按任意一条模型名即可复制")
                msgs.extend(models)
                msgs.append("切换：/model <上面某个名字>\n恢复默认：/model reset")
            else:
                msgs.append("（获取模型列表失败，可直接 /model <name> 尝试切换）")
            return msgs
        if rest.lower() == "reset":
            if chat_id:
                _CHAT_MODEL.pop(chat_id, None)
            return [f"已恢复默认模型：{default}"]
        target = rest.split()[0]
        models = await list_upstream_models(cfg)
        if models and target not in models:
            hint = [f"❌ 模型 {target} 不在上游支持列表中。", "👇 可选："]
            hint.extend(models)
            return hint
        if chat_id:
            _CHAT_MODEL[chat_id] = target
        return [f"✅ 已切换到：{target}"]

    return [f"未知命令：{cmd}，输入 /help 查看帮助"]


# ---- Boss 派单 ----

async def _dispatch(
    user_text: str,
    cfg: OpenClawSettings,
    fs_client: FeishuClient,
    chat_id: str | None,
) -> list[str]:
    state = load_state()
    if not state.employees:
        return ["👥 团队还没有员工，用 /hire 招人后再派单，或 /help 看用法"]

    model = get_effective_model(cfg, chat_id)
    dispatch_msgs = build_dispatch_messages(user_text)
    try:
        raw = await _call_chat_completions(cfg, dispatch_msgs, model)
    except Exception as e:
        print(f"[openclaw.service] 派单 LLM 失败: {type(e).__name__}: {e}")
        return [f"派单失败（LLM 不可用：{type(e).__name__}），稍后再试～"]

    try:
        plan = parse_dispatch_json(raw)
    except Exception as e:
        print(f"[openclaw.service] 派单 JSON 解析失败: {e}；raw={raw!r}")
        return ["派单失败：模型输出不是合法 JSON，稍后再试～"]

    emp_name = plan.get("employee")
    task = plan.get("task") or user_text
    reason = plan.get("reason") or ""

    if not emp_name:
        return [f"🤔 我没找到合适的员工来干这事。原因：{reason}"]

    emp = state.find(emp_name)
    if emp is None:
        return [
            f"⚠️ 模型选的员工「{emp_name}」不在花名册里。原因：{reason}",
            "输入 /team 看看现有员工，或 /hire 招人",
        ]

    # 派单：往员工群发消息
    forward = f"【Boss 派单】\n{task}\n\n—— 转自虾仁花旦"
    ok = await fs_client.send_to_chat(emp.chat_id, forward)
    if not ok:
        return [
            f"❌ 派单到「{emp.name}」失败（可能 bot 没进那个群），任务未送达。",
            f"任务内容：{task}",
        ]

    return [
        f"✅ 已派给 {emp.name}",
        f"任务：{task}",
        f"理由：{reason}",
    ]


_NEWS_INTENT_RE = re.compile(
    r"(最新|今天|最近|拉一下|来一份|来一波|给我).{0,6}(热点|新闻|资讯|动态|快讯|消息)"
    r"|(AI|ai).{0,4}(热点|新闻|资讯|动态)"
    r"|热点(推送|来一下|来一波|来一份)?$"
    r"|今天有什么(新|热点|大事)"
)


def _is_news_intent(text: str) -> bool:
    t = text.strip()
    if not t or t.startswith("/"):
        return False
    return bool(_NEWS_INTENT_RE.search(t))


async def answer(
    user_text: str,
    cfg: OpenClawSettings,
    chat_id: str | None = None,
    fs_client: FeishuClient | None = None,
) -> list[str]:
    if not user_text:
        return ["请在 @我 后面写下你想说的～"]

    # 1) 命令优先
    cmd_reply = await _handle_command(user_text, cfg, chat_id, fs_client)
    if cmd_reply is not None:
        return cmd_reply

    # 1.5) 自然语言意图：要 AI 热点 —— 直接抓最新推到当前群
    if _is_news_intent(user_text) and fs_client is not None and chat_id:
        asyncio.create_task(_run_news_and_ack(fs_client, chat_id, target_chat_id=chat_id))
        return ["🚀 正在抓当天最新 AI 热点，30~60 秒后送到这个群～"]

    # 2) 如果消息发生在某个员工群里，走「直答」（避免自己派给自己）
    state = load_state()
    is_employee_chat = chat_id in {e.chat_id for e in state.list_all()}

    if is_employee_chat or fs_client is None:
        model = get_effective_model(cfg, chat_id)
        messages = [
            {"role": "system", "content": cfg.system_prompt},
            {"role": "user", "content": user_text},
        ]
        try:
            reply = await _call_chat_completions(cfg, messages, model)
        except Exception as e:
            print(f"[openclaw.service] LLM 调用失败 model={model}: {type(e).__name__}: {e}")
            return [f"AI 暂时不可用（{type(e).__name__}），请稍后再试～"]
        text = (reply or "").strip() or "(空回复)"
        return [text]

    # 3) 主群 —— boss 派单
    return await _dispatch(user_text, cfg, fs_client, chat_id)


def split_for_feishu(text: str, limit: int = FEISHU_TEXT_MAX) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    buf: list[str] = []
    used = 0
    for para in text.split("\n"):
        add = len(para) + 1
        if used + add > limit and buf:
            chunks.append("\n".join(buf))
            buf, used = [], 0
        if add > limit:
            for i in range(0, len(para), limit):
                chunks.append(para[i:i + limit])
            continue
        buf.append(para)
        used += add
    if buf:
        chunks.append("\n".join(buf))
    return chunks
