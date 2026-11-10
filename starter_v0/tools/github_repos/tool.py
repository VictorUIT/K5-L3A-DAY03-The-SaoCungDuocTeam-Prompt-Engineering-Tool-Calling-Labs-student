from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err

ALLOWED_SORTS = {"stars", "updated"}


def github_repo_search(query: str = "", sort: str = "stars", limit: int = 5) -> dict[str, Any]:
    """Search public GitHub repositories. GITHUB_TOKEN is optional (raises the rate limit)."""
    try:
        query = (query or "").strip()
        if not query:
            raise ValueError("query must not be empty")
        sort = (sort or "stars").strip().lower()
        if sort not in ALLOWED_SORTS:
            raise ValueError(f"sort must be one of {sorted(ALLOWED_SORTS)}, got {sort!r}")
        limit = max(1, min(int(limit or 5), 20))

        headers = {"Accept": "application/vnd.github+json", "User-Agent": "AI20k-Day03-Research-Agent"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "sort": sort, "order": "desc", "per_page": limit},
            headers=headers,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        items = []
        for repo in response.json().get("items", [])[:limit]:
            url = repo.get("html_url")
            if not url:
                continue
            stars = repo.get("stargazers_count") or 0
            language = repo.get("language") or "n/a"
            items.append({
                "title": repo.get("full_name") or url,
                "url": url,
                "source": "github.com",
                "summary": f"{repo.get('description') or ''} (★ {stars}, {language})".strip(),
                "stars": stars,
                "updated_at": repo.get("pushed_at") or repo.get("updated_at"),
            })
        return {"tool": "github_repo_search", "query": query, "sort": sort, "items": items}
    except Exception as exc:
        return err("github_repo_search", exc)
