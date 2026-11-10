---
name: wiki
track: bonus
kind: live_api
provider: Wikipedia REST API (no key)
requires_env: []
inputs: [query, lang, limit]
outputs: [items]
side_effect: false
---
# wiki

Searches Wikipedia (`vi` or `en`) via the public REST endpoint
`https://{lang}.wikipedia.org/w/rest.php/v1/search/page` and returns
`items` with `title`, `url`, `source`, `summary` (description + excerpt),
the same shape as `lookup`, so `format` can render them.

Use for background / definitions of a concept, person or organization
("Transformer là gì", "tiểu sử Andrej Karpathy"). Not for news or anything
time-sensitive (use `lookup` with `topic=news`).

Guardrails: empty `query` and unsupported `lang` return an error dict without
calling the network; `limit` is coerced to int and clamped to 1–10.
