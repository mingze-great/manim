"""AI 热点抓取 & 摘要 & 推送

信源（每天 09:00 抓最近 24h 的新东西）：
  - HuggingFace Daily Papers（JSON）
  - arXiv cs.AI / cs.CL / cs.LG（Atom）
  - Hacker News (Algolia)：AI 关键词 + points > 80
  - 官方博客 RSS：OpenAI / Anthropic / DeepMind
  - 中文源 RSS：机器之心 / 量子位
  - X 大 V 通过 RSSHub 桥接：Sam Altman / Andrej / Yann LeCun

流程：抓 -> 归一化 -> 去重 -> LLM 打分挑 5~10 条 -> 每条生成一句中文摘要 -> 逐条发到 AI热点群。
"""
from __future__ import annotations

import asyncio
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.openclaw.config import OpenClawSettings, get_openclaw_settings
from app.openclaw.feishu import FeishuClient
from app.openclaw.team import load_state

# ---- 配置 ----

CHINA_TZ = timezone(timedelta(hours=8))
LOOKBACK_HOURS = 24  # AI 实时性强，只推昨天 09:00 到现在的新内容
LOOKBACK_HOURS_ARXIV = 24  # 论文也严格 24h

# 员工名（虾仁花旦的花名册里的）
AI_HOTSPOT_EMPLOYEE = "AI热点"

# RSSHub 公共实例（可换成自建）
RSSHUB = "https://rsshub.app"

# 用户答：混合中英 + 加 X 大 V + 重产品行业
RSS_FEEDS: list[tuple[str, str]] = [
    # ============ 大厂官方博客（一手信息） ============
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("DeepMind", "https://deepmind.google/blog/rss.xml"),

    # ============ 社区综述 & 播客 ============
    # TLDR AI —— 每日 AI 早报（真日更，24h 窗口下几乎每天都有）
    ("TLDR AI", "https://tldr.tech/api/rss/ai"),
    # Latent Space (swyx & Alessio) —— AI 圈头部播客
    ("Latent Space", "https://www.latent.space/feed"),
    # 注：AI News (buttondown.com/ainews) 2025-04 后停更，已剔除

    # ============ 顶尖独立评论 & 领导者 blog ============
    # Simon Willison —— AI 领域最勤更的独立博客，几乎日更
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
    # Jack Clark（Anthropic 联合创始人）—— 相当于 Anthropic 内部视角
    ("Import AI", "https://jack-clark.net/feed/"),
    # Ethan Mollick —— 最有影响力的 AI 应用评论者
    ("One Useful Thing", "https://www.oneusefulthing.org/feed"),

    # ============ 新产品 / 新模型 ============
    ("Product Hunt AI", "https://www.producthunt.com/feed?category=artificial-intelligence"),

    # ============ 学术（比例压低）============
    ("arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI"),
    ("arXiv cs.CL", "https://rss.arxiv.org/rss/cs.CL"),

    # ============ 中文行业媒体 ============
    ("量子位", "https://www.qbitai.com/feed"),

    # 注：Anthropic 官方无公开 RSS，用 Jack Clark 的 Import AI 替代；
    #     HuggingFace / RSSHub / Reddit 从这台服务器直连超时，
    #     X 大 V 需要出海代理或付费 RSSHub 实例，暂时靠 AI News 综述覆盖 X 内容。
]

# 每源保留上限：arXiv 一天几百篇要截断，其余基本天然就少
MAX_PER_SOURCE_DEFAULT = 30
MAX_PER_SOURCE_ARXIV = 15  # arXiv 压到 15 篇内，避免淹没社区源

HN_ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"
HF_DAILY = "https://huggingface.co/api/daily_papers"


# ---- 数据结构 ----

@dataclass
class NewsItem:
    source: str
    title: str
    url: str
    summary: str = ""            # 原始摘要（可能是 HTML）
    published: Optional[datetime] = None
    score: float = 0.0           # LLM 打分后填
    zh_brief: str = ""           # LLM 一句中文摘要

    def key(self) -> str:
        """去重键：URL 优先，其次标题归一化"""
        u = re.sub(r"[#?].*$", "", self.url).rstrip("/")
        return u or re.sub(r"\W+", "", self.title.lower())


# ---- 抓取工具 ----

def _clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def _parse_time(s: str) -> Optional[datetime]:
    if not s:
        return None
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(s.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _within_window(dt: Optional[datetime]) -> bool:
    if dt is None:
        return True  # 没时间戳的默认收进来
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    return dt >= cutoff


async def _fetch(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        r = await client.get(url, timeout=25, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 openclaw-newsbot"})
        if r.status_code == 200 and r.text:
            return r.text
        print(f"[news] fetch {url} -> HTTP {r.status_code}")
    except Exception as e:  # noqa: BLE001
        print(f"[news] fetch {url} 失败: {type(e).__name__}: {e}")
    return None


def _parse_rss(source: str, xml_text: str) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"[news] {source} XML 解析失败: {e}")
        return items
    # RSS 2.0
    for it in root.iter("item"):
        title = _clean((it.findtext("title") or ""))
        link = (it.findtext("link") or "").strip()
        desc = _clean(it.findtext("description") or "")
        pub = _parse_time(it.findtext("pubDate") or "")
        if not title or not link:
            continue
        items.append(NewsItem(source=source, title=title, url=link,
                              summary=desc, published=pub))
    # Atom
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for it in root.findall(".//a:entry", ns):
        title = _clean((it.findtext("a:title", default="", namespaces=ns)))
        link_el = it.find("a:link", ns)
        link = link_el.get("href") if link_el is not None else ""
        summ = _clean(it.findtext("a:summary", default="", namespaces=ns))
        pub = _parse_time(it.findtext("a:updated", default="", namespaces=ns)
                          or it.findtext("a:published", default="", namespaces=ns))
        if not title or not link:
            continue
        items.append(NewsItem(source=source, title=title, url=link,
                              summary=summ, published=pub))
    return items


async def _fetch_rss(client: httpx.AsyncClient, source: str, url: str) -> list[NewsItem]:
    text = await _fetch(client, url)
    if not text:
        return []
    items = _parse_rss(source, text)
    items.sort(key=lambda x: x.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    cap = MAX_PER_SOURCE_ARXIV if source.startswith("arXiv") else MAX_PER_SOURCE_DEFAULT
    return items[:cap]


async def _fetch_hn(client: httpx.AsyncClient) -> list[NewsItem]:
    since = int((datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).timestamp())
    params = {
        "query": "AI OR LLM OR OpenAI OR Anthropic OR GPT OR Claude OR Gemini OR DeepSeek",
        "tags": "story",
        "numericFilters": f"created_at_i>{since},points>80",
        "hitsPerPage": 30,
    }
    try:
        r = await client.get(HN_ALGOLIA, params=params, timeout=20)
        hits = r.json().get("hits", [])
    except Exception as e:  # noqa: BLE001
        print(f"[news] HN 抓取失败: {e}")
        return []
    items = []
    for h in hits:
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        title = _clean(h.get("title") or "")
        if not title:
            continue
        pub = datetime.fromtimestamp(h.get("created_at_i", 0), tz=timezone.utc)
        points = h.get("points", 0)
        comments = h.get("num_comments", 0)
        items.append(NewsItem(
            source="HackerNews",
            title=title,
            url=url,
            summary=f"{points} 分 / {comments} 评论",
            published=pub,
        ))
    return items


async def _fetch_github_trending_ai(client: httpx.AsyncClient) -> list[NewsItem]:
    """GitHub search: 昨天以来创建的、带 AI/LLM/agent 相关 topic、star > 30 的仓库。"""
    since_date = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).strftime("%Y-%m-%d")
    queries = [
        f"stars:>30 created:>{since_date} topic:llm",
        f"stars:>30 created:>{since_date} topic:agent",
        f"stars:>30 created:>{since_date} topic:ai",
    ]
    items: list[NewsItem] = []
    seen_urls: set[str] = set()
    for q in queries:
        try:
            r = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "stars", "order": "desc", "per_page": 10},
                timeout=15,
                headers={"Accept": "application/vnd.github+json",
                         "User-Agent": "openclaw-newsbot"},
            )
            data = r.json()
        except Exception as e:  # noqa: BLE001
            print(f"[news] github {q} 失败: {e}")
            continue
        for repo in data.get("items", []):
            url = repo.get("html_url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            desc = _clean(repo.get("description") or "")
            stars = repo.get("stargazers_count", 0)
            items.append(NewsItem(
                source="GitHub Trending",
                title=f"⭐{stars} {repo.get('full_name')}",
                url=url,
                summary=desc,
                published=_parse_time(repo.get("created_at", "")),
            ))
    return items


async def _fetch_openrouter_new_models(client: httpx.AsyncClient) -> list[NewsItem]:
    """OpenRouter 上最近上架的模型 —— 新模型第一时间出现的地方。"""
    try:
        r = await client.get("https://openrouter.ai/api/v1/models", timeout=20)
        models = r.json().get("data", [])
    except Exception as e:  # noqa: BLE001
        print(f"[news] openrouter 失败: {e}")
        return []
    # created 字段是 unix 时间戳；按创建时间倒序取窗口内的
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS * 2)).timestamp()
    fresh = [m for m in models if (m.get("created") or 0) >= cutoff]
    fresh.sort(key=lambda m: m.get("created", 0), reverse=True)
    items: list[NewsItem] = []
    for m in fresh[:10]:
        mid = m.get("id") or ""
        name = m.get("name") or mid
        ctx = m.get("context_length", 0)
        desc = _clean(m.get("description") or "")
        pub = datetime.fromtimestamp(m.get("created", 0), tz=timezone.utc)
        items.append(NewsItem(
            source="OpenRouter",
            title=f"新模型上架: {name}（{ctx} ctx）",
            url=f"https://openrouter.ai/{mid}",
            summary=desc,
            published=pub,
        ))
    return items


async def _fetch_hf_daily(client: httpx.AsyncClient) -> list[NewsItem]:
    text = await _fetch(client, HF_DAILY)
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = []
    for row in data[:30]:
        paper = row.get("paper") or {}
        pid = paper.get("id")
        title = _clean(paper.get("title", ""))
        summ = _clean(paper.get("summary", ""))
        pub = _parse_time(row.get("publishedAt") or paper.get("publishedAt") or "")
        upvotes = paper.get("upvotes", 0)
        if not title or not pid:
            continue
        items.append(NewsItem(
            source="HF Daily Papers",
            title=title,
            url=f"https://huggingface.co/papers/{pid}",
            summary=f"upvotes={upvotes} · {summ}",
            published=pub,
        ))
    return items


# ---- 汇总 ----

async def collect_all() -> list[NewsItem]:
    async with httpx.AsyncClient() as client:
        # HuggingFace / Reddit 从服务器直连超时，用其他源覆盖
        tasks: list = [
            _fetch_hn(client),
            _fetch_github_trending_ai(client),
            _fetch_openrouter_new_models(client),
        ]
        for source, url in RSS_FEEDS:
            tasks.append(_fetch_rss(client, source, url))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: list[NewsItem] = []
    for r in results:
        if isinstance(r, Exception):
            print(f"[news] source 异常: {r}")
            continue
        merged.extend(r or [])

    # 时间窗过滤
    filtered = [i for i in merged if _within_window(i.published)]
    # 去重
    seen: dict[str, NewsItem] = {}
    for it in filtered:
        k = it.key()
        if k not in seen:
            seen[k] = it
    return list(seen.values())


# ---- LLM 打分 & 中文摘要 ----

RANK_SYS = (
    "你是资深 AI 行业分析师。给你一批过去 24 小时的 AI 圈动态。用户要求「实时 + 有用」，"
    "为国内做 AI 产品/工程的人挑最有价值的 5~10 条。宁缺毋滥，没那么多好内容就少推几条。\n\n"
    "🎯 优先级（越靠前越重要）：\n"
    "  1. 大厂官方发布：OpenAI / DeepMind 官方博客、OpenRouter 新模型上架\n"
    "  2. 头部社区评论：Simon Willison / Latent Space / TLDR AI 里当天的重要观察\n"
    "  3. 新产品 & 新代码：Product Hunt AI、GitHub Trending 新起项目、Hacker News AI 热帖\n"
    "  4. 中文行业动态：量子位当天报道\n"
    "  5. arXiv 论文：默认一条都不要选。只有当天出现真正现象级的成果（例如 GPT/Claude/Gemini "
    "级别新模型、影响行业格局的技术突破、社区疯传的必读之作）才可以破例，最多 1 条。"
    "普通增量工作、榜单刷分、benchmark 变体、领域调优、综述类论文，一律不选。"
    "简单标准：如果不确定「大多数从业者今晚会不会讨论」，就不选。\n"
    "  6. 排除：重复内容、纯广告、单纯 star 攒榜的 GitHub 项目、纯八卦推特。\n\n"
    "严格按下面 JSON 格式回复，不要任何多余文字：\n"
    "{\"picks\": [{\"idx\": <原编号>, \"score\": 0~10, \"zh\": \"一句中文摘要，突出关键信息与影响\"}]}"
)


async def rank_and_summarize(items: list[NewsItem], cfg: OpenClawSettings) -> list[NewsItem]:
    if not items:
        return []
    from app.openclaw.service import _call_chat_completions, get_effective_model

    catalog_lines = []
    for i, it in enumerate(items):
        ts = it.published.astimezone(CHINA_TZ).strftime("%m-%d %H:%M") if it.published else "-"
        snippet = (it.summary or "")[:180]
        catalog_lines.append(f"{i}. [{it.source}][{ts}] {it.title}\n   {snippet}")
    user_prompt = "以下是候选（编号从 0 开始）：\n" + "\n".join(catalog_lines)

    model = get_effective_model(cfg, None)
    raw = await _call_chat_completions(
        cfg,
        [{"role": "system", "content": RANK_SYS},
         {"role": "user", "content": user_prompt}],
        model,
    )
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(m.group(0)) if m else {}
    except Exception as e:  # noqa: BLE001
        print(f"[news] LLM 打分 JSON 解析失败: {e}；raw={raw[:200]}")
        return []

    picks = parsed.get("picks") or []
    out: list[NewsItem] = []
    for p in picks:
        idx = p.get("idx")
        if not isinstance(idx, int) or idx < 0 or idx >= len(items):
            continue
        it = items[idx]
        it.score = float(p.get("score") or 0)
        it.zh_brief = (p.get("zh") or "").strip()
        out.append(it)
    out.sort(key=lambda x: x.score, reverse=True)
    return out[:10]


# ---- 发飞书 ----

def format_item_msg(idx: int, it: NewsItem) -> str:
    ts = it.published.astimezone(CHINA_TZ).strftime("%m-%d %H:%M") if it.published else ""
    head = f"#{idx} · {it.source}" + (f" · {ts}" if ts else "")
    body = it.zh_brief or _clean(it.summary)[:200]
    return f"{head}\n{it.title}\n{body}\n{it.url}"


async def push_daily(chat_id: Optional[str] = None) -> dict:
    """跑一次抓取+发送，返回结果统计。chat_id 不传时从花名册找 AI热点。"""
    cfg = get_openclaw_settings()

    if chat_id is None:
        state = load_state()
        emp = state.find(AI_HOTSPOT_EMPLOYEE)
        if emp is None:
            return {"ok": False, "error": f"花名册没有 {AI_HOTSPOT_EMPLOYEE}"}
        chat_id = emp.chat_id

    t0 = time.time()
    items = await collect_all()
    print(f"[news] 抓取到 {len(items)} 条，用时 {time.time()-t0:.1f}s")
    if not items:
        return {"ok": False, "error": "抓不到任何新闻"}

    ranked = await rank_and_summarize(items, cfg)
    print(f"[news] 精选 {len(ranked)} 条")
    if not ranked:
        return {"ok": False, "error": "LLM 挑不出内容"}

    fs = FeishuClient(cfg)
    date_str = datetime.now(CHINA_TZ).strftime("%Y-%m-%d")
    sources = sorted({it.source for it in ranked})

    parts: list[str] = [f"☀️ AI 热点日报 · {date_str}（{len(ranked)} 条）"]
    for i, it in enumerate(ranked, 1):
        parts.append(format_item_msg(i, it))
    parts.append(f"—— 数据源：{'、'.join(sources)}")
    full = "\n\n".join(parts)

    from app.openclaw.service import split_for_feishu
    sent = 0
    for chunk in split_for_feishu(full):
        if await fs.send_to_chat(chat_id, chunk):
            sent += 1

    return {"ok": True, "picked": len(ranked), "sent": sent, "sources": sources}


# ---- 调度 ----

_SCHED = None


def start_scheduler() -> None:
    """随主进程启动。09:00 Asia/Shanghai 触发。"""
    global _SCHED
    if _SCHED is not None:
        return
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _SCHED = AsyncIOScheduler(timezone=CHINA_TZ)
    _SCHED.add_job(
        _run_push_daily_safe,
        CronTrigger(hour=9, minute=0),
        id="openclaw_ai_hotspot_daily",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _SCHED.start()
    print("[openclaw.news] scheduler started -- AI 热点每天 09:00 (Asia/Shanghai) 推送")


async def _run_push_daily_safe() -> None:
    try:
        result = await push_daily()
        print(f"[openclaw.news] 定时任务结果: {result}")
    except Exception as e:  # noqa: BLE001
        print(f"[openclaw.news] 定时任务异常: {type(e).__name__}: {e}")


def shutdown_scheduler() -> None:
    global _SCHED
    if _SCHED is not None:
        _SCHED.shutdown(wait=False)
        _SCHED = None
