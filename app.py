from __future__ import annotations

import json
import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType

PROJECT_ROOT = Path(__file__).parent / "starter_v0"
PUBLIC_PAGE = Path(__file__).parent / "public" / "index.html"
sys.path.insert(0, str(PROJECT_ROOT))

from chat import run_model_tool_loop, trim_history
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools

load_lab_env(PROJECT_ROOT)

PROVIDER_NAME = os.getenv("AGENT_PROVIDER", "openrouter")
MODEL = os.getenv("AGENT_MODEL") or None
PROMPT_PATH = Path(os.getenv("AGENT_SYSTEM_PROMPT", PROJECT_ROOT / "artifacts/system_prompt.md"))
TOOLS_PATH = Path(os.getenv("AGENT_TOOLS", PROJECT_ROOT / "artifacts/tools.yaml"))
MAX_TOOL_ROUNDS = int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "4"))
HISTORY_WINDOW = int(os.getenv("AGENT_HISTORY_WINDOW", "5"))
MAX_MESSAGE_LENGTH = 20_000

SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
OPENAI_TOOLS = to_openai_tools(load_tool_declarations(TOOLS_PATH))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1_000_000
logger = logging.getLogger("research_agent.vercel")


@lru_cache(maxsize=1)
def get_provider() -> Any:
    return make_provider(PROVIDER_NAME)


def _read_history(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("history must be a list")

    message_limit = max(0, HISTORY_WINDOW) * 2
    recent = value[-message_limit:] if message_limit else []
    history: list[dict[str, str]] = []
    for item in recent:
        if not isinstance(item, dict):
            raise ValueError("history items must be objects")
        role, content = item.get("role"), item.get("content")
        if role not in {"user", "assistant"}:
            raise ValueError("history roles must be user or assistant")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("history content must be a non-empty string")
        if len(content) > MAX_MESSAGE_LENGTH:
            raise ValueError("history message is too long")
        history.append({"role": role, "content": content})
    return trim_history(history, HISTORY_WINDOW)


@app.errorhandler(BadRequest)
def handle_bad_request(error: BadRequest):
    return jsonify(error="invalid_request", message="Request body must be valid JSON"), 400


@app.errorhandler(UnsupportedMediaType)
def handle_unsupported_media_type(error: UnsupportedMediaType):
    return jsonify(error="invalid_request", message="Content-Type must be application/json"), 415


@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(error: RequestEntityTooLarge):
    return jsonify(error="request_too_large", message="Request body must be no larger than 1 MB"), 413


@app.get("/")
def index():
    return send_file(PUBLIC_PAGE)


@app.get("/api/health")
def health():
    return jsonify(
        ok=True,
        provider=PROVIDER_NAME,
        model=MODEL,
    )


@app.post("/api/reset")
def reset():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify(error="invalid_request", message="Request body must be a JSON object"), 400
    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
        return jsonify(error="invalid_request", message="valid session_id is required"), 400
    return jsonify(ok=True)


@app.post("/api/chat")
def chat():
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify(error="invalid_request", message="Request body must be a JSON object"), 400

        session_id = data.get("session_id")
        if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
            return jsonify(error="invalid_request", message="valid session_id is required"), 400

        message = data.get("message")
        if not isinstance(message, str) or not message.strip():
            return jsonify(error="invalid_request", message="message must be a non-empty string"), 400
        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify(error="invalid_request", message="message is too long"), 400

        history = _read_history(data.get("history", []))
        provider = get_provider()
        result = run_model_tool_loop(
            provider=provider,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *history,
                {"role": "user", "content": message.strip()},
            ],
            tools=OPENAI_TOOLS,
            model=MODEL or getattr(provider, "default_model", None),
            max_tool_rounds=MAX_TOOL_ROUNDS,
        )

        for event in result.get("tool_events", []):
            payload = json.dumps(event.get("result"), ensure_ascii=False, default=str)
            if len(payload) > 3000:
                payload = payload[:3000] + "...<truncated>"
            logger.info("tool=%s result=%s", event.get("tool", "unknown"), payload)

        return jsonify(
            reply=result.get("assistant_text") or "Agent không trả về nội dung văn bản.",
            status=result.get("status", "answered"),
            tool_events=result.get("tool_events", []),
        )
    except ValueError as exc:
        return jsonify(error="invalid_request", message=str(exc)), 400
    except Exception as exc:
        logger.exception("Agent request failed: %s: %s", type(exc).__name__, exc)
        return jsonify(
            error="agent_request_failed",
            message="Agent request failed. Check the Vercel runtime logs.",
        ), 502


if __name__ == "__main__":
    app.run(
        host=os.getenv("AGENT_HOST", "127.0.0.1"),
        port=int(os.getenv("AGENT_PORT", "8000")),
    )
