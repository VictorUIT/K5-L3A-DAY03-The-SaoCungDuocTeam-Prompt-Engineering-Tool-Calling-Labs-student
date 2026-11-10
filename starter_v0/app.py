"""Streamlit UI for the Day 03 Research Agent.

Run:   streamlit run app.py          (from starter_v0/, with .venv active)
Share: cloudflared tunnel --url http://localhost:8501

It reuses the exact multi-round tool loop from chat.py, so the UI behaves like
`python chat.py`, and every turn is logged to transcripts/*.transcript.json.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import ARTIFACTS_DIR, ROOT, now_iso, run_model_tool_loop, safe_slug, trim_history, write_transcript
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
TRANSCRIPTS_DIR = ROOT / "transcripts"

TOOL_HELP = {
    "clarify": "Hỏi lại khi thiếu thông tin / xin xác nhận trước khi gửi",
    "timeline": "Tweet mới của một tài khoản X",
    "social_search": "Tweet theo chủ đề (Top / Latest)",
    "lookup": "Tìm web & tin tức (Tavily)",
    "fetch": "Đọc nội dung một URL (Firecrawl)",
    "format": "Gom kết quả thành bản tin markdown",
    "send": "Gửi bản tin lên Telegram (chỉ sau khi xác nhận)",
    "policy": "Tra chính sách nội bộ công ty",
    "papers": "Tìm paper arXiv",
    "paper_text": "Đọc text của một paper arXiv",
    "wiki": "Kiến thức nền từ Wikipedia (mới)",
    "hn_search": "Bài đăng Hacker News (mới)",
    "github_repos": "Repo mã nguồn mở trên GitHub (mới)",
    "hf_models": "Model trên Hugging Face (mới)",
}

SAMPLE_QUESTIONS = [
    "Tin tức AI hôm nay có gì nổi bật?",
    "Lấy 3 tweet mới nhất của Andrej Karpathy",
    "Transformer trong học máy là gì?",
    "Trên Hacker News gần đây mọi người bàn gì về AI agents?",
    "Tìm 3 repo agent framework nhiều sao nhất trên GitHub",
    "Model tiếng Việt nào được tải nhiều nhất trên Hugging Face?",
    "Tóm tắt bài này giúp mình",
    "Đăng bản tin AI hôm nay lên Telegram",
]

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")


# ---------------- session state ----------------

def new_session(provider_name: str, model: str | None, version: str) -> None:
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
        "history_window": 5,
        "max_tool_rounds": 4,
        "source": "streamlit_ui",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    st.session_state.history = []      # what the model sees (user/assistant text)
    st.session_state.display = []      # what the page shows (incl. tool rounds)
    st.session_state.session_key = (provider_name, model, version)


# ---------------- sidebar ----------------

with st.sidebar:
    st.header("Cấu hình")
    provider_name = st.selectbox("Provider", ["gemini", "openrouter", "openai", "anthropic", "ollama"], index=0)
    model = st.text_input("Model (để trống = mặc định của provider)", value="").strip() or None
    version = st.text_input("Version label", value="v3").strip() or "v3"
    if st.button("🆕 Cuộc trò chuyện mới", use_container_width=True):
        new_session(provider_name, model, version)

    st.divider()
    st.subheader("Tool của agent")
    try:
        declared = [item["name"] for item in load_tool_declarations(TOOLS_PATH)]
    except Exception as exc:  # broken YAML should not kill the UI
        declared = []
        st.error(f"Không đọc được tools.yaml: {exc}")
    for name in declared:
        st.markdown(f"- `{name}`: {TOOL_HELP.get(name, '')}")

if st.session_state.get("session_key") != (provider_name, model, version):
    new_session(provider_name, model, version)

# ---------------- main ----------------

st.title("🔎 Research Agent")
st.caption(
    f"Provider **{provider_name}** · artifact `{st.session_state.transcript['artifact_version']}` · "
    f"transcript `{st.session_state.transcript_path.name}`"
)

if not st.session_state.display:
    st.info("Thử một câu hỏi mẫu (bấm để gửi), hoặc tự gõ ở ô bên dưới.")
    cols = st.columns(2)
    for index, question in enumerate(SAMPLE_QUESTIONS):
        if cols[index % 2].button(question, key=f"sample_{index}", use_container_width=True):
            st.session_state.pending = question
            st.rerun()


def render_rounds(rounds: list[dict[str, Any]]) -> None:
    calls = [call for record in rounds for call in record.get("tool_calls", [])]
    if not calls:
        return
    label = "🔧 Tool calls: " + ", ".join(call["name"] for call in calls)
    with st.expander(label):
        for record in rounds:
            for event in record.get("tool_results", []):
                st.markdown(f"**{event['tool']}**")
                st.code(json.dumps(event.get("args", {}), ensure_ascii=False, indent=2), language="json")
                result = event.get("result", {})
                preview = json.dumps(result, ensure_ascii=False, indent=2, default=str)
                st.code(preview[:3000] + ("\n...<truncated>" if len(preview) > 3000 else ""), language="json")


for entry in st.session_state.display:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
        if entry["role"] == "assistant":
            render_rounds(entry.get("rounds", []))

user_text = st.chat_input("Hỏi agent...") or st.session_state.pop("pending", None)

if user_text:
    st.session_state.display.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    tools = to_openai_tools(load_tool_declarations(TOOLS_PATH))
    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, 5),
        {"role": "user", "content": user_text},
    ]
    transcript = st.session_state.transcript
    turn_record: dict[str, Any] = {
        "turn_index": len(transcript["turns"]) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    with st.chat_message("assistant"):
        with st.spinner("Agent đang suy nghĩ và gọi tool..."):
            try:
                result = run_model_tool_loop(
                    provider=make_provider(provider_name),
                    messages=messages,
                    tools=tools,
                    model=model,
                    max_tool_rounds=4,
                )
                turn_record.update(result)
                answer = result["assistant_text"] or "(không có nội dung trả lời)"
                st.session_state.history += [
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": answer},
                ]
            except Exception as exc:
                answer = f"⚠️ Lỗi provider: `{type(exc).__name__}: {exc}`"
                turn_record.update({"status": "provider_error", "error": f"{type(exc).__name__}: {exc}"})
        st.markdown(answer)
        render_rounds(turn_record.get("rounds", []))

    st.session_state.display.append({"role": "assistant", "content": answer, "rounds": turn_record.get("rounds", [])})
    turn_record["ended_at"] = now_iso()
    transcript["turns"].append(turn_record)
    write_transcript(st.session_state.transcript_path, transcript)
