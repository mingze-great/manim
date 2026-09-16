"""HR 招人向导。

触发：在 hr 员工群里说「招人 / 招聘 / 新员工 / 加人 / hire」等词。
三步向导（状态存进程内内存，重启会丢，但一次招聘就一分钟走完，可接受）：

  step 1 (name):     请起个花名（如：采购、市场）
  step 2 (chat_id):  把「虾仁花旦」拉进新员工群，把该群 chat_id 发给我
  step 3 (role):     一句话描述职责
  step 4 (confirm):  确认 / 取消

用户直接说 /hire <name> <chat_id> <role> 仍走原有快捷路径（不动 service.py 的 /hire）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.openclaw.team import CHAT_ID_RE, hire as _team_hire, load_state


HR_EMPLOYEE = "hr"

_TRIGGER_RE = re.compile(r"(招人|招聘|新员工|加人|hire|new hire)", re.IGNORECASE)
_CANCEL_RE = re.compile(r"^(取消|退出|cancel|quit|exit)\s*$", re.IGNORECASE)


@dataclass
class HrDraft:
    name: str = ""
    chat_id: str = ""
    role: str = ""


@dataclass
class HrState:
    step: int = 0  # 0 尚未开始；1..4
    draft: HrDraft = field(default_factory=HrDraft)


_STATES: dict[str, HrState] = {}


def _key(chat_id: str, user_open_id: str) -> str:
    return f"{chat_id}::{user_open_id or 'anon'}"


def is_hr_chat(chat_id: Optional[str]) -> bool:
    if not chat_id:
        return False
    emp = load_state().find(HR_EMPLOYEE)
    return bool(emp and emp.chat_id == chat_id)


async def handle_hr_message(
    chat_id: str,
    user_open_id: str,
    text: str,
    fs_client=None,
) -> Optional[list[str]]:
    """如果在 hr 群且识别为招人流程，返回回复；否则返回 None 走原有链路。"""
    if not is_hr_chat(chat_id):
        return None
    t = (text or "").strip()
    if not t:
        return None

    k = _key(chat_id, user_open_id)
    state = _STATES.get(k)

    # 用户随时可以取消
    if state and _CANCEL_RE.match(t):
        _STATES.pop(k, None)
        return ["已取消本次招人流程。"]

    # 没在流程中：只有命中触发词才启动，否则不接手（让原有链路走）
    if state is None:
        if not _TRIGGER_RE.search(t):
            return None
        _STATES[k] = HrState(step=1)
        return [
            "👋 好嘞，我们开始招新员工。",
            "1/3 请给他/她起一个花名（例如 采购 / 市场 / 客服），只要一个词。",
            "（随时可回复「取消」退出）",
        ]

    # Step 1 → 收 name
    if state.step == 1:
        if len(t) > 20 or "\n" in t:
            return ["花名太长了，一个词就好，比如「采购」。"]
        # 重名检测
        if load_state().find(t) is not None:
            return [f"「{t}」这个花名已经在花名册里啦，请换一个。"]
        state.draft.name = t
        state.step = 2
        return [
            f"👍 花名收到：{t}",
            "2/3 请先把「虾仁花旦」拉进新员工群，然后把该群的 chat_id 发给我。",
            "chat_id 长这样：oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ]

    # Step 2 → 收 chat_id + 校验 bot 在群
    if state.step == 2:
        cid = t.split()[0]
        if not CHAT_ID_RE.match(cid):
            return ["❌ chat_id 格式不对，应形如 oc_ 开头 32 位十六进制。请重发。"]
        # 校验 bot 是否已经在群
        if fs_client is not None:
            info = await fs_client.chat_info(cid)
            if info is None:
                return [
                    f"❌ 我没法访问 {cid}。可能是「虾仁花旦」还没被拉进群，或应用权限不够。",
                    "请先把 bot 拉进群，再重发 chat_id。",
                ]
        state.draft.chat_id = cid
        state.step = 3
        return [
            "✅ 群已连通。",
            "3/3 请用一句话说清这位员工的职责（越具体越容易被派到活）。",
        ]

    # Step 3 → 收 role
    if state.step == 3:
        if len(t) < 4:
            return ["职责太短了，请用一句话说清楚。"]
        state.draft.role = t
        state.step = 4
        d = state.draft
        return [
            "📇 请确认：",
            f"  花名：{d.name}",
            f"  群：{d.chat_id}",
            f"  职责：{d.role}",
            "回复「确认」入职，回复「取消」放弃。",
        ]

    # Step 4 → 确认
    if state.step == 4:
        if re.match(r"^(确认|ok|yes|好|是)\s*$", t, re.IGNORECASE):
            d = state.draft
            _team_hire(d.name, d.chat_id, d.role)
            _STATES.pop(k, None)
            return [
                f"🎉 已录用 {d.name}",
                "以后 @虾仁花旦 提相关需求会自动派到 TA 那儿。",
                "输入 /team 查看花名册。",
            ]
        if _CANCEL_RE.match(t):
            _STATES.pop(k, None)
            return ["已取消本次招人流程。"]
        return ["请回复「确认」或「取消」。"]

    return None
