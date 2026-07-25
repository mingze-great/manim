import re
from pathlib import Path
from typing import Any

from app.utils.llm_factory import LLMFactory


SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9._\-]+"),
    re.compile(r"root@[\w.:-]+"),
    re.compile(r"/opt/[^\s，。；;)）]+"),
    re.compile(r"[A-Z]:\\[^\s，。；;)）]+"),
]


DEFAULT_ENTRIES: list[dict[str, str]] = [
    {
        "title": "火柴人工作流",
        "source": "内置引导",
        "route": "/stickman-workflow",
        "content": "火柴人工作流支持输入标题自动生成视频，也支持自定义文案、选择声音、素材库、背景模板或上传背景。自定义文案和目标时长不能同时选择。",
    },
    {
        "title": "邀请码兑换",
        "source": "内置引导",
        "route": "/profile",
        "content": "有邀请码或兑换码的用户可以进入个人中心，在兑换码区域输入后开通对应套餐和火柴人权限。",
    },
    {
        "title": "合作者工作台",
        "source": "内置引导",
        "route": "/partner",
        "content": "合作者可以在合作者工作台查看自己推荐的用户，并创建非敏感的邀请码给推荐用户使用。",
    },
    {
        "title": "推荐归属与分佣",
        "source": "内置引导",
        "route": "/partner",
        "content": "用户通过合作者的推广链接注册，或兑换合作者创建的邀请码后，平台会记录推荐归属。合作者只能查看自己的推荐用户、订单和佣金，不能进入管理员后台；管理员可以统一查看和结算。",
    },
    {
        "title": "图片模式与套餐权限",
        "source": "内置引导",
        "route": "/stickman-workflow",
        "content": "火柴人视频支持素材库匹配、实时生成场景图和混合补图。页面只展示当前套餐允许的选项；素材库套餐用户保持默认素材匹配，不会看到不可用的实时生图能力。",
    },
    {
        "title": "参考图生成素材库",
        "source": "内置引导",
        "route": "/docs",
        "content": "管理员可以在火柴人工作流素材库页面上传一张参考图，先生成两张风格样图。确认风格后再批量生成覆盖常见情绪和场景的图片，并自动建立 materials.json；完成启用后用户即可选择该素材库。",
    },
    {
        "title": "我的作品",
        "source": "内置引导",
        "route": "/history",
        "content": "生成完成的视频和内容可以在我的作品中查看、回访和下载。",
    },
]


class PlatformAssistantKnowledgeBase:
    def __init__(self, entries: list[dict[str, str]] | None = None, repo_root: Path | None = None):
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]
        self._manual_entries = entries
        self._entries_cache: list[dict[str, str]] | None = None

    @property
    def entries(self) -> list[dict[str, str]]:
        if self._manual_entries is not None:
            return self._manual_entries
        if self._entries_cache is None:
            self._entries_cache = self._load_entries()
        return self._entries_cache

    def search(self, query: str, page_path: str = "", module: str = "", limit: int = 5) -> list[dict[str, str]]:
        terms = self._tokenize(" ".join([query, page_path, module]))
        scored: list[tuple[int, dict[str, str]]] = []
        for entry in self.entries:
            haystack = " ".join([entry.get("title", ""), entry.get("content", ""), entry.get("route", "")]).lower()
            score = 0
            for term in terms:
                if term and term.lower() in haystack:
                    score += 3 if term.startswith("/") else 1
            route = entry.get("route", "")
            if page_path and route and page_path.startswith(route):
                score += 5
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _score, entry in scored[:limit]] or DEFAULT_ENTRIES[:limit]

    def _load_entries(self) -> list[dict[str, str]]:
        entries = list(DEFAULT_ENTRIES)
        candidate_files = [
            "AGENTS.md",
            "PROJECT_STATE.md",
            "rules/vibe-coding.md",
            "rules/quality-gates.md",
            "rules/skill-usage.md",
            "specs/sc1-stickman-workflow-spec.md",
            "specs/development-control-spec.md",
            "frontend/src/pages/Docs/index.tsx",
        ]
        for relative in candidate_files:
            path = self.repo_root / relative
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for chunk in self._chunk_text(text):
                entries.append(
                    {
                        "title": self._title_from_chunk(chunk, relative),
                        "source": relative,
                        "content": chunk,
                        "route": self._route_for_text(chunk),
                    }
                )
        return entries

    def _chunk_text(self, text: str, max_chars: int = 700) -> list[str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        chunks: list[str] = []
        current: list[str] = []
        size = 0
        for line in lines:
            if current and size + len(line) > max_chars:
                chunks.append("\n".join(current))
                current = []
                size = 0
            current.append(line)
            size += len(line)
        if current:
            chunks.append("\n".join(current))
        return chunks

    def _title_from_chunk(self, chunk: str, source: str) -> str:
        for line in chunk.splitlines():
            cleaned = line.strip("# ").strip()
            if cleaned:
                return cleaned[:40]
        return source

    def _route_for_text(self, text: str) -> str:
        route_map = [
            ("/stickman-workflow", ["火柴人", "素材库", "成片", "字幕", "场景图"]),
            ("/profile", ["兑换码", "邀请码", "个人中心", "套餐"]),
            ("/partner", ["合作者", "推荐", "分佣"]),
            ("/history", ["我的作品", "下载", "历史"]),
            ("/docs", ["帮助中心", "教程", "使用手册"]),
        ]
        for route, keywords in route_map:
            if route in text or any(keyword in text for keyword in keywords):
                return route
        return ""

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r"/[\w\-/]+|[A-Za-z0-9_\-]+|[\u4e00-\u9fff]{2,}", text)
        shortcuts = []
        for keyword in [
            "火柴人", "素材库", "邀请码", "兑换码", "合作者", "推荐归属", "分佣", "作品",
            "时长", "声音", "背景", "参考图", "样图", "实时生图", "混合补图",
        ]:
            if keyword in text:
                shortcuts.append(keyword)
        return list(dict.fromkeys(words + shortcuts))


class PlatformAssistantService:
    def __init__(self, knowledge_base: PlatformAssistantKnowledgeBase | Any | None = None):
        self.knowledge_base = knowledge_base or PlatformAssistantKnowledgeBase()

    async def answer(self, message: str, page_path: str = "", module: str = "") -> dict[str, Any]:
        hits = self.knowledge_base.search(message, page_path=page_path, module=module)
        messages = self.build_messages(message, page_path=page_path, module=module, hits=hits)
        try:
            client = LLMFactory.get_client()
            answer = await client.chat(messages=messages, model=LLMFactory.get_chat_model(), temperature=0.2)
        except Exception:
            answer = self._fallback_answer(message, hits)
        return {
            "answer": self._sanitize(answer),
            "suggestedActions": self._suggested_actions(hits),
            "sources": [{"title": hit.get("title", ""), "source": hit.get("source", "")} for hit in hits[:3]],
        }

    def build_messages(
        self,
        message: str,
        page_path: str = "",
        module: str = "",
        hits: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        selected = hits if hits is not None else self.knowledge_base.search(message, page_path=page_path, module=module)
        context = "\n\n".join(
            f"【{item.get('title', '')} | {item.get('source', '')}】\n{self._sanitize(item.get('content', ''))}"
            for item in selected
        )
        user_content = (
            f"当前页面：{page_path or '未知'}\n"
            f"当前模块：{module or '未知'}\n"
            f"用户问题：{message}\n\n"
            f"可用知识：\n{context}"
        )
        return [
            {
                "role": "system",
                "content": (
                    "你是平台内置 AI 助手，面向第一次使用平台的小白用户。"
                    "只根据提供的知识回答，给出清晰步骤和平台入口。"
                    "不要暴露服务器路径、账号、密钥、部署细节或管理员敏感操作。"
                    "如果问题涉及后台敏感信息，只解释普通用户可做什么。"
                ),
            },
            {"role": "user", "content": user_content},
        ]

    def _fallback_answer(self, message: str, hits: list[dict[str, str]]) -> str:
        lines = ["你可以按下面步骤操作："]
        for item in hits[:3]:
            route = item.get("route", "")
            title = item.get("title", "相关功能")
            lines.append(f"- 打开 {title}{f'（{route}）' if route else ''}，按页面提示完成。")
        if "火柴人" in message or "视频" in message:
            lines.append("- 如果只是想快速出片，先在火柴人工作流输入标题，其他选项保持默认。")
        return "\n".join(lines)

    def _suggested_actions(self, hits: list[dict[str, str]]) -> list[dict[str, str]]:
        label_map = {
            "/stickman-workflow": "去火柴人工作流",
            "/profile": "去个人中心兑换码",
            "/partner": "去合作者工作台",
            "/history": "去我的作品",
            "/docs": "去帮助中心",
        }
        actions: list[dict[str, str]] = []
        seen = set()
        for item in hits:
            route = item.get("route", "")
            if not route or route in seen:
                continue
            seen.add(route)
            actions.append({"label": label_map.get(route, f"打开{item.get('title', '页面')}"), "route": route})
        return actions[:4]

    def _sanitize(self, text: str) -> str:
        sanitized = text or ""
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub("【敏感信息已隐藏】", sanitized)
        return sanitized


assistant_service = PlatformAssistantService()
