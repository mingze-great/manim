"""员工花名册 & 派单

结构：
  Employee: name / chat_id / role（一句话职责，用于 LLM 派单选人）

Boss (虾仁花旦) 收到需求 → LLM 依据 role 选一个员工 → 通过 FeishuClient.send_to_chat
向对应群发派单消息。

持久化：openclaw_state.json（放在 backend/ 目录），/hire /fire 后立即落盘。
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

STATE_FILE = Path(__file__).resolve().parents[2] / "openclaw_state.json"


@dataclass
class Employee:
    name: str
    chat_id: str
    role: str  # 一句话职责，例如 "记录/查询个人和团队账目"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TeamState:
    employees: dict[str, Employee] = field(default_factory=dict)
    # boss 自身（即虾仁花旦所在的主群/私聊）不算员工，无需存

    def add(self, e: Employee) -> None:
        self.employees[e.name] = e

    def remove(self, name: str) -> bool:
        return self.employees.pop(name, None) is not None

    def find(self, name: str) -> Optional[Employee]:
        return self.employees.get(name)

    def list_all(self) -> list[Employee]:
        return list(self.employees.values())


# ---- 内置默认花名册（首次启动写入 state 文件）----
DEFAULT_EMPLOYEES: list[Employee] = [
    Employee(
        name="hr",
        chat_id="oc_eeaa7f2a7d71c4ffdb427ac00420d85c",
        role="负责招新员工、员工入职流程、团队人员管理；也可以做通用行政咨询",
    ),
    Employee(
        name="记账",
        chat_id="oc_34d40aee58d2f27487b816364b9d60d6",
        role="记录/查询个人与团队账目、开销、报销、账单相关",
    ),
    Employee(
        name="manim监控",
        chat_id="oc_56bc924baf36ef1c5ec65490c7ca6c9c",
        role="manim 视频平台的运维、监控、告警、报错排查",
    ),
    Employee(
        name="日程助手",
        chat_id="oc_71297c33eff238e07c2bb16b9378823f",
        role="日程安排、会议提醒、时间规划、待办事项",
    ),
    Employee(
        name="AI热点",
        chat_id="oc_115e26e6ba94c13eecbc3dea1c9b895a",
        role="AI 行业热点、模型新闻、技术趋势、资讯汇总",
    ),
]


# ---- 持久化 ----
_STATE: Optional[TeamState] = None


def load_state() -> TeamState:
    global _STATE
    if _STATE is not None:
        return _STATE
    state = TeamState()
    if STATE_FILE.exists():
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            for e in raw.get("employees", []):
                state.add(Employee(**e))
        except Exception as exc:  # noqa: BLE001
            print(f"[openclaw.team] 读取 {STATE_FILE} 失败: {exc}；使用默认花名册")
    if not state.employees:
        for e in DEFAULT_EMPLOYEES:
            state.add(e)
        _save(state)
    _STATE = state
    return state


def _save(state: TeamState) -> None:
    payload = {"employees": [e.to_dict() for e in state.list_all()]}
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def hire(name: str, chat_id: str, role: str) -> Employee:
    state = load_state()
    e = Employee(name=name, chat_id=chat_id, role=role)
    state.add(e)
    _save(state)
    return e


def fire(name: str) -> bool:
    state = load_state()
    ok = state.remove(name)
    if ok:
        _save(state)
    return ok


# ---- LLM 派单选人 ----

CHAT_ID_RE = re.compile(r"^oc_[a-f0-9]{32}$")


def format_roster_for_llm() -> str:
    state = load_state()
    lines = []
    for i, e in enumerate(state.list_all(), 1):
        lines.append(f"{i}. {e.name}：{e.role}")
    return "\n".join(lines) or "（当前没有员工）"


DISPATCH_SYS_PROMPT = (
    "你是虾仁花旦（Boss），只负责把用户的需求派给合适的员工。你从不亲自执行任务，也不"
    "对任务本身作出实质性回答。\n\n"
    "员工名单如下（编号. 名字：职责）：\n"
    "{roster}\n\n"
    "请阅读用户消息，从名单里挑出最合适的一位员工。严格按下列 JSON 格式回复，不要"
    "任何多余文字：\n"
    "{{\"employee\": \"员工名字\", \"task\": \"用一句话把需求交代给他/她（第二人称）\", "
    "\"reason\": \"为什么派给他/她（一句话）\"}}\n\n"
    "如果确实没有合适的员工（例如需求超出所有员工职责范围），返回：\n"
    "{{\"employee\": null, \"task\": null, \"reason\": \"简述原因\"}}"
)


def build_dispatch_messages(user_text: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": DISPATCH_SYS_PROMPT.format(roster=format_roster_for_llm()),
        },
        {"role": "user", "content": user_text},
    ]


def parse_dispatch_json(raw: str) -> dict:
    """LLM 有时会外面套 ``` 或加解释文字，用简单规则抠出 JSON。"""
    s = raw.strip()
    # 去 markdown fence
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    # 找第一个 { 到最后一个 }
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m:
        raise ValueError(f"未找到 JSON 结构：{raw[:200]}")
    return json.loads(m.group(0))
