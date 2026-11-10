---
name: hn_search
track: bonus
kind: live_api
provider: Hacker News Algolia API (no key)
requires_env: []
inputs: [query, sort, limit]
outputs: [items]
side_effect: false
---
# hn_search

Searches Hacker News stories via `https://hn.algolia.com/api/v1/search`
(`sort=relevance`) or `/search_by_date` (`sort=date`). Returns `items` with
`title`, `url` (the article, or the HN thread if the story has no link),
`source`, `summary` (points, comments, HN thread link), `points`, `created_at`.

Use when the user explicitly asks about Hacker News / HN / dân dev đang bàn gì.
Not for X/Twitter (use `social_search`) or general news (use `lookup`).

Guardrails: empty `query` / unknown `sort` return an error dict without a
network call; `limit` is coerced to int and clamped to 1–20; hits without
`objectID` are skipped.
