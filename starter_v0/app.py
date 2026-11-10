"""Streamlit UI for the Day 03 Research Agent.

Run:   streamlit run app.py          (from starter_v0/, with .venv active)
Share: cloudflared tunnel --url http://localhost:8501

It reuses the exact multi-round tool loop from chat.py, so the UI behaves like
`python chat.py`, and every turn is logged to transcripts/*.transcript.json.

Layout
- 💬 Trò chuyện : chat with the agent, live tool progress, clickable tool bar,
                  yes/no buttons when the agent asks for confirmation.
- 🧰 Bộ công cụ : every installed tool as a card (status, usage) + a playground
                  that calls a tool directly, without the model (great for demos).
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from typing import Any

import streamlit as st

from chat import ARTIFACTS_DIR, ROOT, now_iso, run_model_tool_loop, safe_slug, trim_history, write_transcript
from providers import make_provider
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from ui_shared import (
    HISTORY_WINDOW, MAX_TOOL_ROUNDS, PROVIDERS, SAMPLE_QUESTIONS, USER_KEY_FIELDS,
    meta, override_env, summarize_result, tool_label,
)
from versioning import artifact_version_dict, build_artifact_version

SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
TRANSCRIPTS_DIR = ROOT / "transcripts"

PREVIEW_CHARS = 3000


VIEW_CHAT = "💬 Trò chuyện"
VIEW_TOOLS = "🧰 Bộ công cụ"

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")


# ---------------- helpers ----------------



def session_keys() -> dict[str, str]:
    keys = {}
    for env_name, _ in USER_KEY_FIELDS:
        value = (st.session_state.get(f"key_{env_name}") or "").strip()
        if value:
            keys[env_name] = value
    return keys


@st.cache_resource
def _env_lock() -> threading.Lock:
    """One lock per server process (shared by every viewer), so keys never leak across sessions."""
    return threading.Lock()


def user_env():
    """This viewer's keys as env vars, only for the duration of their turn / tool call."""
    return override_env(session_keys(), _env_lock())


def missing_env(names: list[str]) -> list[str]:
    keys = session_keys()
    return [name for name in names if not os.getenv(name) and name not in keys]


def tool_ready(name: str) -> bool:
    return name in TOOL_FUNCTIONS and not missing_env(meta(name).get("env", []))


def short_args(args: dict[str, Any]) -> str:
    parts = []
    for key, value in args.items():
        text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else f'"{value}"'
        parts.append(f"{key}={text[:40] + '…' if len(text) > 40 else text}")
    return ", ".join(parts)


def json_preview(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return text[:PREVIEW_CHARS] + ("\n...<truncated>" if len(text) > PREVIEW_CHARS else "")


def tool_usage() -> dict[str, int]:
    counts: dict[str, int] = {}
    for turn in st.session_state.transcript["turns"]:
        for event in turn.get("tool_events", []):
            counts[event["tool"]] = counts.get(event["tool"], 0) + 1
    for run in st.session_state.playground_runs:
        counts[run["tool"]] = counts.get(run["tool"], 0) + 1
    return counts


# ---------------- session state ----------------

def new_session(version: str) -> None:
    provider_name = st.session_state.get("provider", "gemini")
    model = (st.session_state.get("model") or "").strip() or None
    artifact_version = build_artifact_version(version, SYSTEM_PROMPT_PATH, TOOLS_PATH)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version), safe_slug(provider_name), "ui", timestamp])
    st.session_state.transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    st.session_state.transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": model,
        "system_prompt": str(SYSTEM_PROMPT_PATH),
        "tools": str(TOOLS_PATH),
        "history_window": HISTORY_WINDOW,
        "max_tool_rounds": MAX_TOOL_ROUNDS,
        "source": "streamlit_ui",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    st.session_state.history = []        # what the model sees (user/assistant text)
    st.session_state.display = []        # what the page shows (incl. tool rounds)
    st.session_state.playground_runs = []
    st.session_state.version_used = version
    st.session_state.pop("pending", None)
    st.session_state.busy = False


def queue(text: str) -> None:
    """Callback for every 'send' action: stores the question and locks the UI."""
    text = (text or "").strip()
    if not text or st.session_state.get("busy"):
        return
    st.session_state.pending = text
    st.session_state.busy = True
    st.session_state.view = VIEW_CHAT


def on_chat_submit() -> None:
    queue(st.session_state.get("chat_box", ""))


def on_toolbar_pick() -> None:
    name = st.session_state.get("toolbar")
    st.session_state.toolbar = None
    if name:
        queue(meta(name)["prompt"])


st.session_state.setdefault("view", VIEW_CHAT)
st.session_state.setdefault("busy", False)
if "transcript" not in st.session_state:
    new_session("v5")

# Recover from an interrupted run (Stop button / browser refresh mid-answer).
if st.session_state.busy and "pending" not in st.session_state:
    st.session_state.busy = False
busy: bool = st.session_state.busy


# ---------------- declared tools ----------------

try:
    DECLARATIONS = load_tool_declarations(TOOLS_PATH)
    TOOLS_ERROR = None
except Exception as exc:  # broken YAML should not kill the UI
    DECLARATIONS, TOOLS_ERROR = [], exc
DECLARED = [item["name"] for item in DECLARATIONS]


# ---------------- sidebar ----------------

with st.sidebar:
    st.header("⚙️ Cấu hình")
    st.selectbox(
        "Provider",
        list(PROVIDERS),
        format_func=lambda key: PROVIDERS[key]["label"],
        key="provider",
        disabled=busy,
    )
    provider_name: str = st.session_state.provider
    provider_info = PROVIDERS[provider_name]
    st.text_input(
        "Model",
        key="model",
        placeholder=f"mặc định: {provider_info['default']}",
        disabled=busy,
        help="Để trống để dùng model mặc định. Đổi provider/model KHÔNG xoá cuộc trò chuyện, áp dụng từ câu hỏi tiếp theo.",
    )
    model: str | None = (st.session_state.get("model") or "").strip() or None

    lacking = missing_env(provider_info["env"])
    with st.expander("🔑 API key của bạn", expanded=bool(lacking)):
        st.caption(
            "Key chỉ giữ trong phiên trình duyệt này, không lưu trên server, không ghi vào transcript. "
            "Không có key vẫn chạy thử được Wikipedia, Hacker News, GitHub, Hugging Face, arXiv ở trang Bộ công cụ."
        )
        for env_name, label in USER_KEY_FIELDS:
            if env_name in {"GEMINI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"} \
                    and env_name not in provider_info["env"]:
                continue  # only show the key of the selected provider
            st.text_input(label, key=f"key_{env_name}", type="password", disabled=busy,
                          placeholder="đã có trên server" if os.getenv(env_name) else "dán key vào đây")
    lacking = missing_env(provider_info["env"])
    if lacking:
        st.warning(f"Cần `{'`, `'.join(lacking)}` để chat. Nhập ở mục 🔑 phía trên.", icon="🔑")
    else:
        st.success(f"{provider_info['label']} sẵn sàng · `{model or provider_info['default']}`", icon="✅")

    telegram_ready = not missing_env(["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"])
    allow_send = st.toggle(
        "Cho phép gửi Telegram",
        value=telegram_ready,
        disabled=busy or not telegram_ready,
        help="Khi tắt, agent không được dùng công cụ Gửi lên Telegram. Cần TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID.",
    )
    presentation = st.toggle("🎤 Chế độ trình chiếu (chữ to)", value=True)

    st.divider()
    version = st.text_input("Version label", value="v5", help="Áp dụng khi bấm Cuộc trò chuyện mới.").strip() or "v5"
    if st.button("🆕 Cuộc trò chuyện mới", use_container_width=True, type="primary", disabled=busy):
        new_session(version)
        st.rerun()
    st.download_button(
        "⬇️ Tải transcript (.json)",
        data=json.dumps(st.session_state.transcript, ensure_ascii=False, indent=2, default=str),
        file_name=st.session_state.transcript_path.name,
        mime="application/json",
        use_container_width=True,
        disabled=not st.session_state.transcript["turns"],
    )

    with st.expander("🛠 Thông tin kỹ thuật"):
        st.caption(f"Artifact: `{st.session_state.transcript['artifact_version']}`")
        st.caption(f"Version: `{st.session_state.version_used}`")
        st.caption(f"Transcript: `{st.session_state.transcript_path.name}`")
        st.caption(f"History window: {HISTORY_WINDOW} · Max tool rounds: {MAX_TOOL_ROUNDS}")


# ---------------- styles ----------------

base_size = "1.12rem" if presentation else "1rem"
st.markdown(
    f"""
<style>
  .block-container {{ padding-top: 2.2rem; max-width: 1200px; }}
  [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {{ font-size: {base_size}; line-height: 1.6; }}
  .hero {{
    padding: 1.1rem 1.4rem; border-radius: 16px; margin-bottom: .8rem;
    background: linear-gradient(120deg, rgba(99,102,241,.16), rgba(16,185,129,.12));
    border: 1px solid rgba(99,102,241,.25);
  }}
  .hero h1 {{ margin: 0; padding: 0; font-size: {'2.3rem' if presentation else '1.9rem'}; }}
  .hero p {{ margin: .25rem 0 0; opacity: .8; font-size: {base_size}; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .7rem; }}
  .chip {{
    font-size: .82rem; padding: .18rem .65rem; border-radius: 999px;
    background: rgba(127,127,127,.12); border: 1px solid rgba(127,127,127,.22);
  }}
  .toolmeta {{ font-size: .85rem; opacity: .75; }}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------- header ----------------

ready_count = sum(tool_ready(name) for name in DECLARED)
turn_count = len(st.session_state.transcript["turns"])
call_count = sum(tool_usage().values())
st.markdown(
    f"""
<div class="hero">
  <h1>🔎 Research Agent</h1>
  <p>Trợ lý nghiên cứu AI: tìm tin tức, tweet, paper, repo, model và soạn bản tin, có dẫn nguồn.</p>
  <div class="chips">
    <span class="chip">🤖 {provider_info['label']} · {model or provider_info['default']}</span>
    <span class="chip">🧰 {ready_count}/{len(DECLARED)} công cụ sẵn sàng</span>
    <span class="chip">💬 {turn_count} lượt hỏi</span>
    <span class="chip">🔧 {call_count} lần dùng công cụ</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if TOOLS_ERROR:
    st.error(f"Không đọc được tools.yaml: {TOOLS_ERROR}")

view = st.segmented_control("Màn hình", [VIEW_CHAT, VIEW_TOOLS], key="view", label_visibility="collapsed")
if view is None:  # clicking the active segment deselects it, so fall back to chat
    view = VIEW_CHAT


# ---------------- rendering pieces ----------------

def render_rounds(rounds: list[dict[str, Any]]) -> None:
    events = [event for record in rounds for event in record.get("tool_results", [])]
    if not events:
        return
    with st.expander(f"🔧 Xem chi tiết {len(events)} bước dùng công cụ"):
        for index, event in enumerate(events, 1):
            st.markdown(f"**{index}. {tool_label(event['tool'])}** · {summarize_result(event.get('result'))}")
            left, right = st.columns(2)
            left.caption("Tham số")
            left.code(json.dumps(event.get("args", {}), ensure_ascii=False, indent=2), language="json")
            right.caption("Kết quả")
            right.code(json_preview(event.get("result", {})), language="json")


def render_tool_badges(entry: dict[str, Any]) -> None:
    names = [event["tool"] for record in entry.get("rounds", []) for event in record.get("tool_results", [])]
    bits = [tool_label(name) for name in names]
    if entry.get("elapsed") is not None:
        bits.append(f"⏱ {entry['elapsed']:.1f}s")
    if entry.get("provider"):
        bits.append(f"🤖 {entry['provider']}")
    if bits:
        st.caption(" · ".join(bits))


def render_clarify_buttons(entry: dict[str, Any]) -> None:
    clarify = entry.get("clarify") or {}
    options = list(clarify.get("options") or [])
    if not options and clarify.get("response_type") == "yes_no":
        options = ["✅ Có, đồng ý", "❌ Không, huỷ"]
    if not options:
        return
    st.caption("Bấm để trả lời nhanh, hoặc tự gõ ở ô bên dưới:")
    cols = st.columns(min(len(options), 4))
    for index, option in enumerate(options):
        cols[index % len(cols)].button(
            option, key=f"clarify_{len(st.session_state.display)}_{index}",
            on_click=queue, args=(option,), use_container_width=True, disabled=busy,
        )


def run_turn(user_text: str) -> None:
    """Run one agent turn with live progress, then store it in display/history/transcript."""
    st.session_state.display.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    declarations = [item for item in DECLARATIONS if allow_send or item["name"] != "send"]
    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, HISTORY_WINDOW),
        {"role": "user", "content": user_text},
    ]
    transcript = st.session_state.transcript
    turn_record: dict[str, Any] = {
        "turn_index": len(transcript["turns"]) + 1,
        "started_at": now_iso(),
        "provider": provider_name,
        "model": model,
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    started = time.perf_counter()
    clarify: dict[str, Any] | None = None
    with st.chat_message("assistant"):
        with st.status("Agent đang suy nghĩ…", expanded=True) as status:
            tool_started: dict[str, float] = {}

            def on_event(kind: str, payload: dict[str, Any]) -> None:
                if kind == "round_start":
                    label = "🧠 Đang phân tích câu hỏi…" if payload["round"] == 1 else f"🧠 Vòng {payload['round']}: đọc kết quả, quyết định bước tiếp…"
                    status.update(label=label)
                elif kind == "tool_start":
                    tool_started[payload["name"]] = time.perf_counter()
                    status.update(label=f"{tool_label(payload['name'])}…")
                    st.markdown(f"**{tool_label(payload['name'])}** <span class='toolmeta'>· {short_args(payload['args'])}</span>", unsafe_allow_html=True)
                elif kind == "tool_end":
                    took = time.perf_counter() - tool_started.get(payload["tool"], time.perf_counter())
                    st.caption(f"↳ {summarize_result(payload.get('result'))} · {took:.1f}s")

            try:
                with user_env():
                    result = run_model_tool_loop(
                        provider=make_provider(provider_name),
                        messages=messages,
                        tools=to_openai_tools(declarations),
                        model=model,
                        max_tool_rounds=MAX_TOOL_ROUNDS,
                        on_event=on_event,
                    )
                turn_record.update(result)
                answer = result["assistant_text"] or "(không có nội dung trả lời)"
                if result["status"] in ("answered", "waiting_for_user"):
                    st.session_state.history += [
                        {"role": "user", "content": user_text},
                        {"role": "assistant", "content": answer},
                    ]
                if result["status"] == "waiting_for_user":
                    clarify = next(
                        (event["result"] for event in reversed(result["tool_events"])
                         if isinstance(event.get("result"), dict) and event["result"].get("awaiting_user")),
                        None,
                    )
                elapsed = time.perf_counter() - started
                tool_total = len(result["tool_events"])
                final_state = "complete" if result["status"] != "max_tool_rounds" else "error"
                status.update(
                    label=f"Xong trong {elapsed:.1f}s · {tool_total} lần dùng công cụ" if tool_total else f"Trả lời trực tiếp · {elapsed:.1f}s",
                    state=final_state, expanded=False,
                )
            except Exception as exc:
                elapsed = time.perf_counter() - started
                hint = " Nhập API key ở mục 🔑 trong sidebar." if lacking else ""
                answer = f"⚠️ **Lỗi khi gọi {provider_info['label']}:** `{type(exc).__name__}: {exc}`{hint}"
                turn_record.update({"status": "provider_error", "error": f"{type(exc).__name__}: {exc}"})
                status.update(label="Có lỗi xảy ra", state="error", expanded=False)

    st.session_state.display.append({
        "role": "assistant",
        "content": answer,
        "rounds": turn_record.get("rounds", []),
        "elapsed": elapsed,
        "provider": provider_name,
        "clarify": clarify,
    })
    turn_record["ended_at"] = now_iso()
    transcript["turns"].append(turn_record)
    write_transcript(st.session_state.transcript_path, transcript)


# ---------------- view: chat ----------------

def chat_view() -> None:
    # Tool bar: one click = ask the agent a demo question that needs that tool.
    st.pills(
        "Công cụ của agent (bấm để thử)",
        [name for name in DECLARED if allow_send or name != "send"],
        format_func=tool_label,
        key="toolbar",
        on_change=on_toolbar_pick,
        disabled=busy,
    )

    if not st.session_state.display and "pending" not in st.session_state:
        st.markdown("#### 👋 Bắt đầu với một câu hỏi mẫu")
        cols = st.columns(3)
        for index, (icon, question) in enumerate(SAMPLE_QUESTIONS):
            with cols[index % 3]:
                st.button(
                    f"{icon}  {question}", key=f"sample_{index}", on_click=queue, args=(question,),
                    use_container_width=True, disabled=busy,
                )

    last_index = len(st.session_state.display) - 1
    for index, entry in enumerate(st.session_state.display):
        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])
            if entry["role"] == "assistant":
                render_tool_badges(entry)
                render_rounds(entry.get("rounds", []))
                if index == last_index and "pending" not in st.session_state:
                    render_clarify_buttons(entry)

    pending = st.session_state.pop("pending", None)
    if pending:
        try:
            run_turn(pending)
        finally:
            st.session_state.busy = False
        st.rerun()  # re-render with inputs enabled and the new turn in history


# ---------------- view: tools ----------------

def tools_view() -> None:
    usage = tool_usage()
    st.markdown(
        f"#### 🧰 {len(DECLARED)} công cụ agent đang dùng"
        f"<span class='toolmeta'> · agent tự chọn công cụ phù hợp với câu hỏi</span>",
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for index, name in enumerate(DECLARED):
        info = meta(name)
        lacking_env = missing_env(info.get("env", []))
        with cols[index % 3].container(border=True):
            head, badge = st.columns([3, 2])
            head.markdown(f"**{tool_label(name)}**")
            if name not in TOOL_FUNCTIONS:
                badge.markdown(":red-badge[Chưa có code]")
            elif lacking_env:
                badge.markdown(":orange-badge[Thiếu key]")
            elif name == "send" and not allow_send:
                badge.markdown(":gray-badge[Đang tắt]")
            else:
                badge.markdown(":green-badge[Sẵn sàng]")
            st.markdown(f"<span class='toolmeta'>Nguồn: <b>{info.get('source', '')}</b> · {info['group']}</span>", unsafe_allow_html=True)
            st.write(info["desc"])
            footer = f"Đã dùng {usage.get(name, 0)} lần · mã tool: `{name}`"
            if lacking_env:
                footer += f" · cần `{'`, `'.join(lacking_env)}`"
            st.caption(footer)
            if info.get("prompt"):
                st.button(
                    "💬 Hỏi agent", key=f"ask_{name}", on_click=queue, args=(info["prompt"],),
                    use_container_width=True, disabled=busy or (name == "send" and not allow_send),
                    help=info["prompt"],
                )

    st.divider()
    st.markdown("#### 🧪 Chạy thử từng công cụ (không qua AI)")
    st.caption("Gọi thẳng công cụ mà không cần AI, để thấy từng công cụ tự hoạt động được.")
    runnable = [name for name in DECLARED if name in TOOL_FUNCTIONS]
    if not runnable:
        st.info("Không có công cụ nào để chạy.")
        return
    left, right = st.columns([2, 3])
    with left:
        name = st.selectbox(
            "Công cụ", runnable, format_func=tool_label, key="pg_tool",
        )
        args_text = st.text_area(
            "Tham số (JSON)",
            value=json.dumps(meta(name).get("args", {}), ensure_ascii=False, indent=2),
            height=220,
            key=f"pg_args_{name}",
        )
        if name == "send":
            st.caption("⚠️ Đặt `confirmed: true` sẽ gửi tin nhắn thật lên Telegram.")
        run = st.button("▶️ Chạy thử", type="primary", use_container_width=True, disabled=busy)
    with right:
        if run:
            try:
                args = json.loads(args_text or "{}")
                if not isinstance(args, dict):
                    raise ValueError("Tham số phải là một object JSON.")
            except (json.JSONDecodeError, ValueError) as exc:
                st.error(f"JSON không hợp lệ: {exc}")
            else:
                with st.spinner(f"Đang chạy {tool_label(name)}…"):
                    started = time.perf_counter()
                    try:
                        with user_env():
                            result = TOOL_FUNCTIONS[name](**args)
                    except Exception as exc:
                        result = {"error": type(exc).__name__, "message": str(exc)}
                    took = time.perf_counter() - started
                st.session_state.playground_runs.append({"tool": name, "args": args, "result": result, "took": took})
        if st.session_state.playground_runs:
            last = st.session_state.playground_runs[-1]
            summary = summarize_result(last["result"])
            (st.error if summary.startswith("lỗi") else st.success)(
                f"{tool_label(last['tool'])} · {summary} · {last['took']:.1f}s"
            )
            markdown = last["result"].get("markdown") if isinstance(last["result"], dict) else None
            if isinstance(markdown, str) and markdown.strip():
                with st.container(border=True):
                    st.markdown(markdown)
            st.code(json_preview(last["result"]), language="json")
        else:
            st.info("Chọn một tool, chỉnh tham số nếu muốn, rồi bấm **Chạy thử**.")


# ---------------- main ----------------

if view == VIEW_TOOLS:
    tools_view()
else:
    chat_view()

st.chat_input(
    "Đang trả lời…" if busy else "Hỏi agent bất cứ điều gì về AI…",
    key="chat_box",
    on_submit=on_chat_submit,
    disabled=busy,
)
