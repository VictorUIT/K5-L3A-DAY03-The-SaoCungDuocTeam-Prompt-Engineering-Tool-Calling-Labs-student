from __future__ import annotations

import re
from typing import Any

import requests

from tools._shared import TIMEOUT, err

ALLOWED_LANGS = {"vi", "en"}
HEADERS = {"User-Agent": "AI20k-Day03-Research-Agent/1.0 (educational lab)"}


def _clean(text: str | None) -> str:
    """Wikipedia search excerpts contain <span class="searchmatch"> tags."""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def wiki_search(query: str = "", lang: str = "vi", limit: int = 3) -> dict[str, Any]:
    """Search Wikipedia pages and return title, link and a short excerpt for each hit."""
    try:
        query = (query or "").strip()
        if not query:
            raise ValueError("query must not be empty")
        lang = (lang or "vi").strip().lower()
        if lang not in ALLOWED_LANGS:
            raise ValueError(f"lang must be one of {sorted(ALLOWED_LANGS)}, got {lang!r}")
        limit = max(1, min(int(limit or 3), 10))

        response = requests.get(
            f"https://{lang}.wikipedia.org/w/rest.php/v1/search/page",
            params={"q": query, "limit": limit},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        pages = response.json().get("pages", [])
        items = []
        for page in pages[:limit]:
            key = page.get("key")
            if not key:
                continue
            description = page.get("description") or ""
            excerpt = _clean(page.get("excerpt"))
            items.append({
                "title": page.get("title") or key,
                "url": f"https://{lang}.wikipedia.org/wiki/{key}",
                "source": f"{lang}.wikipedia.org",
                "summary": f"{description}. {excerpt}".strip(". ") if description else excerpt,
            })
        return {"tool": "wiki_search", "query": query, "lang": lang, "items": items}
    except Exception as exc:
        return err("wiki_search", exc)
