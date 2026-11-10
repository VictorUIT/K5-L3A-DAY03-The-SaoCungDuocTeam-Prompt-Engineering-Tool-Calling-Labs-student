"""Shared code for the Vercel serverless functions (files starting with _ are not routes).

The functions reuse starter_v0 as-is: the same system prompt, tools.yaml, tool code and the
multi-round loop from chat.py, so the Vercel app behaves like `python chat.py` and the
Streamlit UI. Serverless instances keep no state between requests, so the browser sends the
chat history with every request and keeps the transcript itself.

API keys: the viewer pastes their own keys in the page; they arrive in the request body, are
exposed as env vars only while that request runs (ui_shared.override_env) and are never logged
or stored. Keys set as Vercel environment variables also work.
"""
from __future__ import annotations

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

STARTER = Path(__file__).resolve().parent.parent / "starter_v0"
sys.path.insert(0, str(STARTER))
os.environ.setdefault("ARXIV_DIR", "/tmp/arxiv_papers")  # the deployment bundle is read-only

from chat import run_model_tool_loop, trim_history  # noqa: E402
from providers import make_provider  # noqa: E402
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools  # noqa: E402
from ui_shared import (  # noqa: E402
    HISTORY_WINDOW, MAX_TOOL_ROUNDS, PROVIDERS, SAMPLE_QUESTIONS, USER_KEY_FIELDS,
    meta, override_env, summarize_result, tool_label,
)
from versioning import build_artifact_version  # noqa: E402

SYSTEM_PROMPT_PATH = STARTER / "artifacts" / "system_prompt.md"
TOOLS_PATH = STARTER / "artifacts" / "tools.yaml"
ALLOWED_KEYS = {name for name, _ in USER_KEY_FIELDS} | {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}
CLOUD_PROVIDERS = [name for name in PROVIDERS if name != "ollama"]  # no local Ollama on Vercel
MAX_MESSAGE_CHARS = 4000
MAX_HISTORY_MESSAGES = 40
PREVIEW_CHARS = 3000


class BadRequest(Exception):
    pass


def declarations() -> list[dict[str, Any]]:
    return load_tool_declarations(TOOLS_PATH)


def artifact_version() -> str:
    return build_artifact_version("vercel", SYSTEM_PROMPT_PATH, TOOLS_PATH).artifact_version


def clean_keys(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {
        name: value.strip()
        for name, value in raw.items()
        if name in ALLOWED_KEYS and isinstance(value, str) and value.strip()
    }


def preview(value: Any) -> Any:
    """Keep responses small: long tool results are cut to a JSON-text preview."""
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= PREVIEW_CHARS:
        return value
    return {"_truncated": True, "preview": text[:PREVIEW_CHARS] + "…"}


def event_view(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": event["tool"],
        "label": tool_label(event["tool"]),
        "args": event.get("args", {}),
        "summary": summarize_result(event.get("result")),
        "result": preview(event.get("result")),
    }


def config() -> dict[str, Any]:
    tools = []
    for item in declarations():
        name = item["name"]
        info = meta(name)
        tools.append({
            "name": name,
            "icon": info["icon"],
            "label": info.get("label", name),
            "source": info.get("source", ""),
            "group": info.get("group", ""),
            "desc": info.get("desc", ""),
            "prompt": info.get("prompt", ""),
            "args": info.get("args", {}),
            "env": info.get("env", []),
            "implemented": name in TOOL_FUNCTIONS,
        })
    return {
        "artifact_version": artifact_version(),
        "providers": {name: {k: PROVIDERS[name][k] for k in ("label", "env", "default")} for name in CLOUD_PROVIDERS},
        "key_fields": [{"env": name, "label": label} for name, label in USER_KEY_FIELDS],
        "server_keys": sorted(name for name in ALLOWED_KEYS if os.getenv(name)),
        "samples": [{"icon": icon, "text": text} for icon, text in SAMPLE_QUESTIONS],
        "tools": tools,
        "history_window": HISTORY_WINDOW,
        "max_tool_rounds": MAX_TOOL_ROUNDS,
    }


def chat(body: dict[str, Any]) -> dict[str, Any]:
    provider_name = body.get("provider") or "gemini"
    if provider_name not in CLOUD_PROVIDERS:
        raise BadRequest(f"provider must be one of {CLOUD_PROVIDERS}")
    model = (body.get("model") or "").strip() or None
    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        raise BadRequest("message is required")
    if len(message) > MAX_MESSAGE_CHARS:
        raise BadRequest(f"message is longer than {MAX_MESSAGE_CHARS} characters")
    history = [
        {"role": item["role"], "content": str(item["content"])[:MAX_MESSAGE_CHARS * 2]}
        for item in (body.get("history") or [])[-MAX_HISTORY_MESSAGES:]
        if isinstance(item, dict) and item.get("role") in ("user", "assistant") and item.get("content")
    ]
    allow_send = bool(body.get("allow_send"))
    tool_decls = [item for item in declarations() if allow_send or item["name"] != "send"]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")},
        *trim_history(history, HISTORY_WINDOW),
        {"role": "user", "content": message.strip()},
    ]

    started = time.perf_counter()
    try:
        with override_env(clean_keys(body.get("keys"))):
            result = run_model_tool_loop(
                provider=make_provider(provider_name),
                messages=messages,
                tools=to_openai_tools(tool_decls),
                model=model,
                max_tool_rounds=MAX_TOOL_ROUNDS,
            )
    except Exception as exc:  # provider errors (missing key, quota, network) go back to the page
        return {
            "status": "provider_error",
            "answer": f"⚠️ **Lỗi khi gọi {PROVIDERS[provider_name]['label']}:** `{type(exc).__name__}: {exc}`",
            "events": [],
            "clarify": None,
            "elapsed": time.perf_counter() - started,
            "provider": provider_name,
            "model": model or PROVIDERS[provider_name]["default"],
        }

    clarify = None
    if result["status"] == "waiting_for_user":
        for event in reversed(result["tool_events"]):
            if isinstance(event.get("result"), dict) and event["result"].get("awaiting_user"):
                clarify = {k: event["result"].get(k) for k in ("question", "response_type", "options")}
                break
    return {
        "status": result["status"],
        "answer": result["assistant_text"] or "(không có nội dung trả lời)",
        "events": [event_view(event) for event in result["tool_events"]],
        "clarify": clarify,
        "elapsed": time.perf_counter() - started,
        "provider": provider_name,
        "model": model or PROVIDERS[provider_name]["default"],
        # only answered / clarify turns go into the model's history (not error or max-rounds text)
        "keep_in_history": result["status"] in ("answered", "waiting_for_user"),
    }


def run_tool(body: dict[str, Any]) -> dict[str, Any]:
    name = body.get("tool")
    if name not in TOOL_FUNCTIONS or name not in {item["name"] for item in declarations()}:
        raise BadRequest("unknown tool")
    args = body.get("args") or {}
    if not isinstance(args, dict):
        raise BadRequest("args must be a JSON object")
    started = time.perf_counter()
    with override_env(clean_keys(body.get("keys"))):
        try:
            result = TOOL_FUNCTIONS[name](**args)
        except Exception as exc:
            result = {"error": type(exc).__name__, "message": str(exc)}
    return {
        "tool": name,
        "label": tool_label(name),
        "summary": summarize_result(result),
        "result": preview(result),
        "took": time.perf_counter() - started,
    }


class JsonHandler(BaseHTTPRequestHandler):
    """Base for the Vercel handlers: JSON in, JSON out, never echoes keys."""

    def send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length > 200_000:
            raise BadRequest("request body too large")
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            raise BadRequest(f"invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise BadRequest("body must be a JSON object")
        return data

    def handle_post(self, action) -> None:
        try:
            self.send_json(200, action(self.read_json()))
        except BadRequest as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, format: str, *args: Any) -> None:  # keep request lines out of logs
        return
