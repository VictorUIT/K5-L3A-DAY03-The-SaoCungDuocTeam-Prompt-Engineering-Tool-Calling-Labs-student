"""Shared UI data and helpers for both front-ends of the Research Agent.

- app.py           Streamlit UI (local / Streamlit Community Cloud)
- api/ + public/   Vercel deployment (static page + Python serverless functions)

Internal tool names (lookup, fetch, ...) must stay in sync with artifacts/tools.yaml and the
eval files; this module only adds the human-friendly labels shown in the UI.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from threading import Lock
from typing import Any, Iterator

HISTORY_WINDOW = 5
MAX_TOOL_ROUNDS = 4

PROVIDERS: dict[str, dict[str, Any]] = {
    "gemini": {"label": "Google Gemini", "env": ["GEMINI_API_KEY"], "default": "gemini-3.5-flash"},
    "openrouter": {"label": "OpenRouter", "env": ["OPENROUTER_API_KEY"], "default": "openai/gpt-4o-mini"},
    "openai": {"label": "OpenAI", "env": ["OPENAI_API_KEY"], "default": "gpt-4o-mini"},
    "anthropic": {"label": "Anthropic", "env": ["ANTHROPIC_API_KEY"], "default": "claude-haiku-4-5-20251001"},
    "ollama": {"label": "Ollama (local)", "env": [], "default": os.getenv("OLLAMA_MODEL", "qwen2.5:7b")},
}

# icon, group, short description, demo prompt (via agent), demo args (direct call), required env vars
TOOL_META: dict[str, dict[str, Any]] = {
    "clarify": {
        "icon": "❓", "group": "Điều phối",
        "label": "Hỏi lại người dùng", "source": "Agent",
        "desc": "Khi câu hỏi thiếu thông tin (tài khoản nào, link nào…) hoặc trước khi đăng/gửi, agent hỏi lại bạn thay vì tự đoán.",
        "prompt": "Tóm tắt bài này giúp mình",
        "args": {"question": "Bạn muốn xem tweet của tài khoản nào?", "response_type": "text"},
    },
    "timeline": {
        "icon": "🐦", "group": "Mạng xã hội",
        "label": "Xem tweet theo tài khoản", "source": "X/Twitter · RapidAPI",
        "desc": "Lấy các bài đăng mới nhất của một người/tài khoản X cụ thể, ví dụ @karpathy.",
        "prompt": "Lấy 3 tweet mới nhất của Andrej Karpathy",
        "args": {"screenname": "karpathy", "limit": 3},
        "env": ["RAPIDAPI_KEY"],
    },
    "social_search": {
        "icon": "💬", "group": "Mạng xã hội",
        "label": "Tìm tweet theo chủ đề", "source": "X/Twitter · RapidAPI",
        "desc": "Tìm xem mọi người trên X đang nói gì về một chủ đề, theo mới nhất hoặc nổi bật nhất.",
        "prompt": "Mọi người trên Twitter đang bàn gì về GPT-5?",
        "args": {"query": "GPT-5", "search_type": "Latest", "limit": 3},
        "env": ["RAPIDAPI_KEY"],
    },
    "lookup": {
        "icon": "🌐", "group": "Web",
        "label": "Tìm kiếm web & tin tức", "source": "Tavily Search",
        "desc": "Tìm kiếm trên Internet như Google: tin tức, sự kiện, thông tin mới, có lọc theo ngày/tuần/tháng.",
        "prompt": "Tin tức AI hôm nay có gì nổi bật?",
        "args": {"query": "AI", "topic": "news", "timeframe": "day", "max_results": 3},
        "env": ["TAVILY_API_KEY"],
    },
    "fetch": {
        "icon": "📄", "group": "Web",
        "label": "Đọc nội dung trang web", "source": "Firecrawl",
        "desc": "Mở một đường link bạn đưa và lấy toàn bộ nội dung bài viết để agent đọc và tóm tắt.",
        "prompt": "Tóm tắt bài này giúp mình: https://en.wikipedia.org/wiki/Large_language_model",
        "args": {"url": "https://en.wikipedia.org/wiki/Large_language_model"},
        "env": ["FIRECRAWL_API_KEY"],
    },
    "format": {
        "icon": "📰", "group": "Trình bày",
        "label": "Soạn bản tin", "source": "Agent",
        "desc": "Gom các kết quả đã tìm được thành một bản tin markdown gọn gàng, có dẫn nguồn.",
        "prompt": "Tìm 3 tin AI hôm nay rồi làm thành bản tin dạng gạch đầu dòng",
        "args": {
            "items": [
                {"title": "Ví dụ tin 1", "url": "https://example.com/1", "source": "Example", "summary": "Tóm tắt tin 1"},
                {"title": "Ví dụ tin 2", "url": "https://example.com/2", "source": "Example", "summary": "Tóm tắt tin 2"},
            ],
            "template": "bullets",
            "headline": "Bản tin demo",
        },
    },
    "send": {
        "icon": "📨", "group": "Gửi đi",
        "label": "Gửi lên Telegram", "source": "Telegram Bot",
        "desc": "Đăng bản tin lên kênh Telegram của nhóm. Luôn hỏi xác nhận trước khi gửi.",
        "prompt": "Đăng bản tin AI hôm nay lên Telegram",
        "args": {"text": "Xin chào từ Research Agent 👋", "confirmed": False},
        "env": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
    },
    "post": {
        "icon": "📣", "group": "Đăng bài",
        "label": "Đăng bài lên X", "source": "X (chế độ thử, không đăng thật)",
        "desc": "Mô phỏng đăng bài công khai lên X (tối đa 280 ký tự). Luôn cần xác nhận, lab không đăng thật.",
        "prompt": "Đăng lên X: Research Agent của nhóm SaoCungDuoc đã chạy thành công!",
        "args": {"content": "Research Agent của nhóm SaoCungDuoc đã chạy thành công!", "confirmed": False},
    },
    "email": {
        "icon": "✉️", "group": "Gửi đi",
        "label": "Gửi email", "source": "Email (chế độ thử, không gửi thật)",
        "desc": "Mô phỏng gửi email: kiểm tra địa chỉ người nhận và xin xác nhận trước khi gửi.",
        "prompt": "Gửi email tóm tắt tin AI hôm nay cho team@example.com",
        "args": {"to": "team@example.com", "content": "Tóm tắt tin AI hôm nay…", "confirmed": False},
    },
    "share_doc": {
        "icon": "📂", "group": "Nội bộ",
        "label": "Chia sẻ tài liệu", "source": "Tài liệu nội bộ (chế độ thử)",
        "desc": "Mô phỏng chia sẻ tài liệu nội bộ cho người khác, phải kiểm tra policy và xác nhận người nhận.",
        "prompt": "Chia sẻ báo cáo nội bộ tuần này cho đối tác bên ngoài partner@example.com",
        "args": {"content": "Báo cáo nội bộ tuần này", "recipient": "partner@example.com", "confirmed": False},
    },
    "policy": {
        "icon": "🏢", "group": "Nội bộ",
        "label": "Tra chính sách công ty", "source": "Tài liệu nội bộ",
        "desc": "Tra cứu quy định nội bộ: trích dẫn nguồn, dữ liệu cá nhân, đăng bài ra ngoài…",
        "prompt": "Theo policy công ty, tweet có được coi là fact không?",
        "args": {"query": "tweet có được coi là fact không", "policy_area": "source_citation", "top_k": 2},
    },
    "papers": {
        "icon": "📚", "group": "Nghiên cứu",
        "label": "Tìm bài báo khoa học", "source": "arXiv",
        "desc": "Tìm các paper nghiên cứu theo chủ đề trên arXiv.",
        "prompt": "Tìm 3 paper về RAG evaluation",
        "args": {"query": "retrieval augmented generation evaluation", "max_results": 3, "sort_by": "relevance"},
    },
    "paper_text": {
        "icon": "📖", "group": "Nghiên cứu",
        "label": "Đọc nội dung bài báo", "source": "arXiv (PDF)",
        "desc": "Tải PDF một paper arXiv theo mã/link và trích nội dung để tóm tắt.",
        "prompt": "Đọc 2 trang đầu paper 1706.03762 và tóm tắt",
        "args": {"arxiv_url": "1706.03762", "max_pages": 2, "max_chars": 3000},
    },
    "wiki": {
        "icon": "🧠", "group": "Kiến thức",
        "label": "Tra cứu Wikipedia", "source": "Wikipedia",
        "desc": "Lấy kiến thức nền: định nghĩa khái niệm, tiểu sử, giới thiệu tổ chức.",
        "prompt": "Transformer trong học máy là gì?",
        "args": {"query": "Transformer", "lang": "vi", "limit": 2},
    },
    "hn_search": {
        "icon": "🟧", "group": "Cộng đồng dev",
        "label": "Tìm trên Hacker News", "source": "Hacker News",
        "desc": "Xem cộng đồng lập trình viên trên Hacker News đang bàn luận gì.",
        "prompt": "Trên Hacker News gần đây mọi người bàn gì về AI agents?",
        "args": {"query": "AI agents", "sort": "date", "limit": 3},
    },
    "github_repos": {
        "icon": "🐙", "group": "Mã nguồn",
        "label": "Tìm dự án trên GitHub", "source": "GitHub",
        "desc": "Tìm thư viện, framework mã nguồn mở theo số sao hoặc mới cập nhật.",
        "prompt": "Tìm 3 repo agent framework nhiều sao nhất trên GitHub",
        "args": {"query": "agent framework", "sort": "stars", "limit": 3},
    },
    "hf_models": {
        "icon": "🤗", "group": "Model AI",
        "label": "Tìm model AI", "source": "Hugging Face",
        "desc": "Tìm model AI tải về/chạy được trên Hugging Face, theo lượt tải hoặc lượt thích.",
        "prompt": "Model tiếng Việt nào được tải nhiều nhất trên Hugging Face?",
        "args": {"query": "vietnamese", "sort": "downloads", "limit": 3},
    },
}

SAMPLE_QUESTIONS = [
    ("🌐", "Tin tức AI hôm nay có gì nổi bật?"),
    ("🐦", "Lấy 3 tweet mới nhất của Andrej Karpathy"),
    ("🧠", "Transformer trong học máy là gì?"),
    ("🟧", "Trên Hacker News gần đây mọi người bàn gì về AI agents?"),
    ("🐙", "Tìm 3 repo agent framework nhiều sao nhất trên GitHub"),
    ("🤗", "Model tiếng Việt nào được tải nhiều nhất trên Hugging Face?"),
]


def meta(name: str) -> dict[str, Any]:
    return TOOL_META.get(name, {"icon": "🔧", "label": name, "source": "", "group": "Khác", "desc": "", "prompt": "", "args": {}})


def tool_label(name: str) -> str:
    """Friendly display name, e.g. '🌐 Tìm kiếm web & tin tức' (internal name stays 'lookup')."""
    info = meta(name)
    return f"{info['icon']} {info.get('label', name)}"


# Keys a viewer can paste into the sidebar (kept only in their browser session, never on disk).
USER_KEY_FIELDS: list[tuple[str, str]] = [
    ("GEMINI_API_KEY", "Gemini API key"),
    ("OPENROUTER_API_KEY", "OpenRouter API key"),
    ("OPENAI_API_KEY", "OpenAI API key"),
    ("ANTHROPIC_API_KEY", "Anthropic API key"),
    ("TAVILY_API_KEY", "Tavily (Tìm kiếm web & tin tức)"),
    ("FIRECRAWL_API_KEY", "Firecrawl (Đọc nội dung trang web)"),
    ("RAPIDAPI_KEY", "RapidAPI (Tweet trên X)"),
]


def summarize_result(result: Any) -> str:
    """One short human line describing a tool result, e.g. '5 kết quả' or 'lỗi: ...'."""
    if not isinstance(result, dict):
        return "xong"
    if result.get("error"):
        message = str(result.get("message") or result.get("error"))
        return "lỗi: " + (message[:80] + "…" if len(message) > 80 else message)
    if result.get("awaiting_user"):
        return "đang chờ người dùng trả lời"
    if result.get("status") == "needs_confirmation":
        return "cần xác nhận trước khi gửi"
    for value in result.values():
        if isinstance(value, list):
            return f"{len(value)} kết quả"
    return "xong"


_ENV_LOCK = Lock()


@contextmanager
def override_env(keys: dict[str, str], lock: Lock = _ENV_LOCK) -> Iterator[None]:
    """Expose a viewer's API keys as env vars only while their request runs.

    Tools and providers read keys with os.getenv, and os.environ is shared by every request in the
    process, so keys are set under a process-wide lock and restored right after.
    """
    keys = {name: value for name, value in keys.items() if value}
    if not keys:
        yield
        return
    with lock:
        previous = {name: os.environ.get(name) for name in keys}
        os.environ.update(keys)
        try:
            yield
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
