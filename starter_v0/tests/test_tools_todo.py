"""Tool Unit Test Challenge - filled in.

Patterns come from test_tools_examples.py. Fixtures are in conftest.py.

Rules:
- Offline only: mock HTTP with `fake_http`, set fake keys with `monkeypatch.setenv`.
- One behaviour per test. Name the test after the behaviour, not the function.
- Done = `pytest tests/ -v` shows 0 skipped, 0 failed.
"""
from __future__ import annotations

import requests

from conftest import FakeResponse
from tools import TOOL_FUNCTIONS

clarify = TOOL_FUNCTIONS["clarify"]
format_tool = TOOL_FUNCTIONS["format"]
send = TOOL_FUNCTIONS["send"]
lookup = TOOL_FUNCTIONS["lookup"]
fetch = TOOL_FUNCTIONS["fetch"]
timeline = TOOL_FUNCTIONS["timeline"]
social_search = TOOL_FUNCTIONS["social_search"]
policy = TOOL_FUNCTIONS["policy"]
wiki = TOOL_FUNCTIONS["wiki"]
hn_search = TOOL_FUNCTIONS["hn_search"]
github_repos = TOOL_FUNCTIONS["github_repos"]
hf_models = TOOL_FUNCTIONS["hf_models"]


def _tweet(tweet_id: str | None, handle: str = "sama", text: str = "hello") -> dict:
    raw = {"screen_name": handle, "text": text}
    if tweet_id is not None:
        raw["tweet_id"] = tweet_id
    return raw


# ---------------- clarify ----------------

def test_clarify_choice_returns_options_and_awaits_user() -> None:
    result = clarify(question="Bạn muốn xem tài khoản nào?", response_type="choice", options=["sama", "karpathy"])

    assert result["options"] == ["sama", "karpathy"]
    assert result["response_type"] == "choice"
    assert result["awaiting_user"] is True


# ---------------- format ----------------

def test_format_sections_groups_items_by_section() -> None:
    items = [
        {"title": "a1", "url": "https://a.com/1", "section": "A"},
        {"title": "b1", "url": "https://b.com/1", "section": "B"},
        {"title": "a2", "url": "https://a.com/2", "section": "A"},
    ]
    markdown = format_tool(items=items, template="sections")["markdown"]

    assert markdown.count("## A") == 1
    assert markdown.count("## B") == 1


def test_format_thread_numbers_items() -> None:
    items = [{"title": f"t{i}", "url": f"https://x.com/{i}"} for i in range(3)]
    lines = format_tool(items=items, template="thread")["markdown"].split("\n\n")

    assert [line.split(" ")[0] for line in lines] == ["1/", "2/", "3/"]


def test_format_empty_items_does_not_crash() -> None:
    assert format_tool(items=None, template="sections")["item_count"] == 0
    assert format_tool(items=[], template="brief")["item_count"] == 0


# ---------------- send (guardrail) ----------------

def test_send_confirmed_posts_to_telegram(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100999")
    calls = fake_http(FakeResponse({"ok": True}))

    result = send(text="Bản tin AI", confirmed=True)

    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert "bot123:abc" in calls[0]["url"]
    assert calls[0]["json"]["chat_id"] == "-100999"
    assert calls[0]["json"]["text"] == "Bản tin AI"
    assert result["status"] == "sent"


def test_send_confirmed_without_env_returns_error_and_no_request(fake_http) -> None:
    calls = fake_http(FakeResponse({"ok": True}))

    result = send(text="Bản tin AI", confirmed=True)

    assert result["error"] == "RuntimeError"
    assert calls == []


# ---------------- lookup ----------------

def test_lookup_without_timeframe_omits_time_range(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    lookup(query="AI", timeframe=None)

    assert "time_range" not in calls[0]["json"]


def test_lookup_string_max_results_is_sent_as_int(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    lookup(query="AI", max_results="3")

    assert calls[0]["json"]["max_results"] == 3


# ---------------- fetch ----------------

def test_fetch_maps_firecrawl_response(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    calls = fake_http(FakeResponse({"data": {
        "markdown": "Nội dung bài",
        "metadata": {"title": "T", "sourceURL": "https://www.openai.com/blog/x"},
    }}))

    result = fetch(url="https://www.openai.com/blog/x")

    assert calls[0]["json"]["url"] == "https://www.openai.com/blog/x"
    assert result["items"][0] == {
        "title": "T", "url": "https://www.openai.com/blog/x",
        "source": "openai.com", "summary": "Nội dung bài",
    }


def test_fetch_truncates_markdown_to_4000_chars(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    fake_http(FakeResponse({"data": {"markdown": "x" * 5000, "metadata": {}}}))

    result = fetch(url="https://example.com")

    assert len(result["items"][0]["summary"]) == 4000


def test_fetch_empty_url_returns_error_without_request(monkeypatch, fake_http) -> None:
    """Regression (B5): an empty url used to be POSTed to Firecrawl and burn a credit."""
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    calls = fake_http(FakeResponse({"data": {}}))

    result = fetch(url="")

    assert result["error"] == "ValueError"
    assert calls == []


# ---------------- timeline / social_search ----------------

def test_timeline_respects_limit_and_skips_items_without_id(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rk")
    raw = [_tweet(None)] + [_tweet(str(i)) for i in range(6)]
    calls = fake_http(FakeResponse({"timeline": raw}))

    result = timeline(screenname="sama", limit=3)

    assert calls[0]["params"] == {"screenname": "sama"}
    assert len(result["items"]) == 3
    assert all(item["url"].startswith("https://x.com/sama/status/") for item in result["items"])


def test_timeline_negative_limit_still_returns_at_least_one(monkeypatch, fake_http) -> None:
    """Regression (B5): limit=-1 used to return all-but-last because of negative slicing."""
    monkeypatch.setenv("RAPIDAPI_KEY", "rk")
    fake_http(FakeResponse({"timeline": [_tweet(str(i)) for i in range(6)]}))

    result = timeline(screenname="sama", limit=-1)

    assert len(result["items"]) == 1


def test_social_search_passes_search_type(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rk")
    calls = fake_http(FakeResponse({"timeline": []}))

    social_search(query="OpenAI", search_type="Top")

    assert calls[0]["url"].endswith("/search.php")
    assert calls[0]["params"] == {"query": "OpenAI", "search_type": "Top"}


def test_social_search_without_key_returns_error_dict(fake_http) -> None:
    calls = fake_http(FakeResponse({"timeline": []}))

    result = social_search(query="OpenAI")

    assert result["error"] == "RuntimeError"
    assert calls == []


# ---------------- policy (local knowledge + trust boundary) ----------------

def test_policy_empty_query_returns_no_results() -> None:
    assert policy(query="")["results"] == []


def test_policy_area_filter_only_returns_that_area() -> None:
    results = policy(query="data privacy personal information", policy_area="data_privacy", top_k=5)["results"]

    assert results
    assert all(hit["policy_area"] == "data_privacy" for hit in results)


def test_policy_instruction_like_lines_go_to_untrusted_text() -> None:
    results = policy(query="citation tweet source tiers", policy_area="source_citation", top_k=10)["results"]

    untrusted = " ".join(line for hit in results for line in hit["untrusted_text"])
    facts = " ".join(hit["facts"] for hit in results)
    assert "viral tweet" in untrusted
    assert "viral tweet" not in facts


# ================ NEW TOOLS (team) ================
# Each new tool: happy path (request + mapping), bad input from the model, failure path.

# ---------------- wiki ----------------

def test_wiki_sends_query_and_maps_pages(fake_http) -> None:
    calls = fake_http(FakeResponse({"pages": [
        {"key": "Transformer_(mô_hình_học_máy)", "title": "Transformer", "description": "Kiến trúc mạng nơ-ron",
         "excerpt": "Một <span class=\"searchmatch\">transformer</span> là..."},
        {"title": "no key -> skipped"},
    ]}))

    result = wiki(query="Transformer", lang="vi", limit=3)

    assert calls[0]["url"] == "https://vi.wikipedia.org/w/rest.php/v1/search/page"
    assert calls[0]["params"] == {"q": "Transformer", "limit": 3}
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["url"] == "https://vi.wikipedia.org/wiki/Transformer_(mô_hình_học_máy)"
    assert "<span" not in item["summary"]
    assert item["summary"].startswith("Kiến trúc mạng nơ-ron")


def test_wiki_empty_query_or_bad_lang_does_not_call_network(fake_http) -> None:
    calls = fake_http(FakeResponse({"pages": []}))

    assert wiki(query="   ")["error"] == "ValueError"
    assert wiki(query="AI", lang="fr")["error"] == "ValueError"
    assert calls == []


def test_wiki_string_limit_is_coerced_and_clamped(fake_http) -> None:
    calls = fake_http(FakeResponse({"pages": []}))

    wiki(query="AI", limit="50")

    assert calls[0]["params"]["limit"] == 10


def test_wiki_http_error_returns_error_dict(fake_http) -> None:
    fake_http(FakeResponse(status_code=503))
    assert wiki(query="AI")["error"] == "HTTPError"


# ---------------- hn_search ----------------

def test_hn_search_relevance_maps_hits_and_falls_back_to_thread_url(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": [
        {"objectID": "1", "title": "Show HN: agent", "url": "https://github.com/x/agent", "points": 120, "num_comments": 30},
        {"objectID": "2", "title": "Ask HN: no link", "url": None, "points": 5},
        {"title": "missing id -> skipped"},
    ]}))

    result = hn_search(query="AI agents", limit=5)

    assert calls[0]["url"] == "https://hn.algolia.com/api/v1/search"
    assert calls[0]["params"] == {"query": "AI agents", "tags": "story", "hitsPerPage": 5}
    assert [item["url"] for item in result["items"]] == [
        "https://github.com/x/agent", "https://news.ycombinator.com/item?id=2",
    ]
    assert result["items"][0]["points"] == 120


def test_hn_search_date_sort_uses_search_by_date(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    hn_search(query="LLM", sort="date")

    assert calls[0]["url"] == "https://hn.algolia.com/api/v1/search_by_date"


def test_hn_search_bad_sort_or_empty_query_does_not_call_network(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    assert hn_search(query="")["error"] == "ValueError"
    assert hn_search(query="AI", sort="Top")["error"] == "ValueError"
    assert calls == []


def test_hn_search_timeout_returns_error_dict(fake_http) -> None:
    fake_http(requests.Timeout("too slow"))
    assert hn_search(query="AI")["error"] == "Timeout"


# ---------------- github_repos ----------------

def test_github_repos_sends_sort_and_maps_repos(monkeypatch, fake_http) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    calls = fake_http(FakeResponse({"items": [
        {"full_name": "org/agent-kit", "html_url": "https://github.com/org/agent-kit",
         "description": "Agent framework", "stargazers_count": 1234, "language": "Python"},
    ]}))

    result = github_repos(query="agent framework", sort="stars", limit=3)

    assert calls[0]["url"] == "https://api.github.com/search/repositories"
    assert calls[0]["params"] == {"q": "agent framework", "sort": "stars", "order": "desc", "per_page": 3}
    assert "Authorization" not in calls[0]["headers"]
    assert result["items"][0]["title"] == "org/agent-kit"
    assert result["items"][0]["stars"] == 1234


def test_github_repos_uses_token_when_present(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    calls = fake_http(FakeResponse({"items": []}))

    github_repos(query="rag")

    assert calls[0]["headers"]["Authorization"] == "Bearer ghp_test"


def test_github_repos_bad_sort_does_not_call_network(fake_http) -> None:
    calls = fake_http(FakeResponse({"items": []}))

    assert github_repos(query="rag", sort="forks")["error"] == "ValueError"
    assert calls == []


def test_github_repos_rate_limited_returns_error_dict(fake_http) -> None:
    fake_http(FakeResponse(status_code=403))
    assert github_repos(query="rag")["error"] == "HTTPError"


# ---------------- hf_models ----------------

def test_hf_models_sends_sort_and_maps_models(fake_http) -> None:
    calls = fake_http(FakeResponse([
        {"id": "vinai/phobert-base", "pipeline_tag": "fill-mask", "downloads": 900, "likes": 40},
        {"pipeline_tag": "no id -> skipped"},
    ]))

    result = hf_models(query="vietnamese", sort="likes", limit=5)

    assert calls[0]["url"] == "https://huggingface.co/api/models"
    assert calls[0]["params"] == {"search": "vietnamese", "sort": "likes", "direction": -1, "limit": 5}
    assert result["items"] == [{
        "title": "vinai/phobert-base", "url": "https://huggingface.co/vinai/phobert-base",
        "source": "huggingface.co", "summary": "task: fill-mask, downloads: 900, likes: 40",
        "downloads": 900, "likes": 40,
    }]


def test_hf_models_empty_query_does_not_call_network(fake_http) -> None:
    calls = fake_http(FakeResponse([]))

    assert hf_models(query=None)["error"] == "ValueError"
    assert calls == []


def test_hf_models_non_numeric_limit_returns_error_dict(fake_http) -> None:
    calls = fake_http(FakeResponse([]))

    assert hf_models(query="llama", limit="many")["error"] == "ValueError"
    assert calls == []


def test_hf_models_http_error_returns_error_dict(fake_http) -> None:
    fake_http(FakeResponse(status_code=500))
    assert hf_models(query="llama")["error"] == "HTTPError"
