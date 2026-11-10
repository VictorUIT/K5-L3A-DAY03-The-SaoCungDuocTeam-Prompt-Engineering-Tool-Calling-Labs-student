"""Small local HTTP server that connects the chatbot page to ResearchAgent."""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent / "starter_v0"
sys.path.insert(0, str(PROJECT_ROOT))

from chat import run_model_tool_loop, trim_history
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools


ROOT = PROJECT_ROOT
PAGE = Path(__file__).parent / "public" / "index.html"
load_lab_env(ROOT)
PROVIDER_NAME = os.getenv("AGENT_PROVIDER", "openrouter")
MODEL = os.getenv("AGENT_MODEL") or None
PROMPT_PATH = Path(os.getenv("AGENT_SYSTEM_PROMPT", ROOT / "artifacts/system_prompt.md"))
TOOLS_PATH = Path(os.getenv("AGENT_TOOLS", ROOT / "artifacts/tools.yaml"))
MAX_TOOL_ROUNDS = int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "4"))
HISTORY_WINDOW = int(os.getenv("AGENT_HISTORY_WINDOW", "5"))
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
OPENAI_TOOLS = to_openai_tools(load_tool_declarations(TOOLS_PATH))
PROVIDER = make_provider(PROVIDER_NAME)
if MODEL is None:
    MODEL = getattr(PROVIDER, "default_model", None)

sessions: dict[str, list[dict[str, str]]] = {}
sessions_lock = threading.Lock()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("research_agent.server")


def log_tool_events(events: list[dict]) -> None:
    """Log tool outcomes while keeping large fetched payloads out of the console."""
    for event in events:
        result = event.get("result")
        serialized = json.dumps(result, ensure_ascii=False, default=str)
        if len(serialized) > 3000:
            serialized = serialized[:3000] + "...<truncated>"
        name = event.get("tool", "unknown")
        args = json.dumps(event.get("args", {}), ensure_ascii=False, default=str)
        failed = isinstance(result, dict) and bool(result.get("error"))
        logger.log(logging.ERROR if failed else logging.INFO,
                   "tool=%s args=%s result=%s", name, args, serialized)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/health":
            return self._json(200, {"ok": True, "provider": PROVIDER_NAME, "model": MODEL})
        if urlparse(self.path).path in {"/", "/index.html"}:
            try:
                body = PAGE.read_bytes()
            except OSError:
                return self._json(500, {"error": "Chat UI file not found", "path": str(PAGE)})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path == "/api/reset":
            try:
                data = self._read_json()
                session_id = data.get("session_id")
                if not isinstance(session_id, str) or not session_id:
                    return self._json(400, {"error": "session_id is required"})
                with sessions_lock:
                    sessions.pop(session_id, None)
                return self._json(200, {"ok": True})
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})

        if urlparse(self.path).path != "/api/chat":
            return self._json(404, {"error": "not_found"})
        try:
            data = self._read_json()
            session_id, message = data.get("session_id"), data.get("message")
            if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
                return self._json(400, {"error": "valid session_id is required"})
            if not isinstance(message, str) or not message.strip():
                return self._json(400, {"error": "message must be a non-empty string"})
            with sessions_lock:
                history = list(sessions.get(session_id, []))

            result = run_model_tool_loop(
                provider=PROVIDER,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *trim_history(history, HISTORY_WINDOW),
                    {"role": "user", "content": message.strip()},
                ],
                tools=OPENAI_TOOLS,
                model=MODEL,
                max_tool_rounds=MAX_TOOL_ROUNDS,
            )
            log_tool_events(result.get("tool_events", []))
            answer = result.get("assistant_text") or "Agent không trả về nội dung văn bản."
            logger.info("agent_response status=%s", result.get("status", "answered"))
            with sessions_lock:
                history.extend([
                    {"role": "user", "content": message.strip()},
                    {"role": "assistant", "content": answer},
                ])
                sessions[session_id] = trim_history(history, HISTORY_WINDOW)
            return self._json(200, {
                "reply": answer,
                "status": result.get("status", "answered"),
                "tool_events": result.get("tool_events", []),
            })
        except (ValueError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": str(exc)})
        except Exception as exc:
            logger.exception("Agent request failed: %s: %s", type(exc).__name__, exc)
            return self._json(502, {"error": "agent_request_failed", "message": str(exc)})

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 1 or length > 1_000_000:
            raise ValueError("request body must be between 1 byte and 1 MB")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def _json(self, status: int, value: dict) -> None:
        body = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main() -> None:
    host = os.getenv("AGENT_HOST", "127.0.0.1")
    port = int(os.getenv("AGENT_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Research Agent UI: http://{host}:{port}/")
    print(f"Provider: {PROVIDER_NAME}; model: {MODEL or '(provider default)'}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
