---
name: github_repos
track: bonus
kind: live_api
provider: GitHub REST API (no key needed; optional GITHUB_TOKEN)
requires_env: []
inputs: [query, sort, limit]
outputs: [items]
side_effect: false
---
# github_repos

Searches public repositories via `https://api.github.com/search/repositories`,
sorted by `stars` (most popular) or `updated` (most recently active). Returns
`items` with `title` (owner/repo), `url`, `source`, `summary` (description,
stars, language), `stars`, `updated_at`.

Use when the user asks for open-source code, libraries, frameworks or repos
("repo agent framework nhiều sao nhất"). Not for papers (use `papers`) or
models (use `hf_models`).

Unauthenticated search is limited to ~10 requests/minute; set `GITHUB_TOKEN`
in `.env` to raise it. Guardrails: empty `query` / unknown `sort` return an
error dict without a network call; `limit` is clamped to 1–20.
