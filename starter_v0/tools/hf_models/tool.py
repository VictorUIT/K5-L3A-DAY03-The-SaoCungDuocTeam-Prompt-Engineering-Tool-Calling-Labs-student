from __future__ import annotations

from typing import Any

import requests

from tools._shared import TIMEOUT, err

ALLOWED_SORTS = {"downloads", "likes"}


def hf_model_search(query: str = "", sort: str = "downloads", limit: int = 5) -> dict[str, Any]:
    """Search models on the Hugging Face Hub (public API, no key)."""
    try:
        query = (query or "").strip()
        if not query:
            raise ValueError("query must not be empty")
        sort = (sort or "downloads").strip().lower()
        if sort not in ALLOWED_SORTS:
            raise ValueError(f"sort must be one of {sorted(ALLOWED_SORTS)}, got {sort!r}")
        limit = max(1, min(int(limit or 5), 20))

        response = requests.get(
            "https://huggingface.co/api/models",
            params={"search": query, "sort": sort, "direction": -1, "limit": limit},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        items = []
        for model in response.json()[:limit]:
            model_id = model.get("id") or model.get("modelId")
            if not model_id:
                continue
            task = model.get("pipeline_tag") or "n/a"
            items.append({
                "title": model_id,
                "url": f"https://huggingface.co/{model_id}",
                "source": "huggingface.co",
                "summary": f"task: {task}, downloads: {model.get('downloads') or 0}, likes: {model.get('likes') or 0}",
                "downloads": model.get("downloads") or 0,
                "likes": model.get("likes") or 0,
            })
        return {"tool": "hf_model_search", "query": query, "sort": sort, "items": items}
    except Exception as exc:
        return err("hf_model_search", exc)
