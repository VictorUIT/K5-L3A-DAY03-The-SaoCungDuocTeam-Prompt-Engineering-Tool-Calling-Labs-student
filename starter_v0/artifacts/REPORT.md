# Day 03 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. **Xong trước 16:30** để làm tài liệu phụ trợ khi demo. Có thể làm thành poster HTML/SVG (`artifacts/poster.html` / `poster.svg`) để show cho team cùng zone.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. **Có thể hoàn thiện sau buổi debate để nộp bài.**

## Team

- Team: SaoCungDuoc (làm cá nhân)
- Members: SaoCungDuoc
- Provider/model: Gemini / gemini-3.5-flash

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

**Research agent cho người làm AI:** hỏi bằng tiếng Việt, agent tự chọn đúng nguồn — X/Twitter (theo tài khoản hoặc chủ đề), tin tức web, đọc một URL, Wikipedia, Hacker News, GitHub, Hugging Face, arXiv, chính sách nội bộ — rồi tổng hợp thành câu trả lời hoặc bản tin. Thiếu thông tin thì **hỏi lại thay vì đoán**; muốn đăng Telegram thì **xin xác nhận trước khi gửi**; câu hỏi ngoài phạm vi (giải toán, viết code) thì từ chối, không gọi tool.

Kết quả eval cố định (20 case, Gemini): **v0 55% → v1 85% → v2 95% → v3 100%**.

**Link dùng thử (deploy):**

> URL: (dán link `https://....trycloudflare.com` sau khi chạy `streamlit run app.py` + `cloudflared tunnel --url http://localhost:8501`)

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại khi thiếu tài khoản/URL/chủ đề; xin xác nhận yes/no trước khi gửi | không |
| timeline | Tweet mới của một tài khoản X (handle không có @) | không |
| social_search | Tweet theo chủ đề, sắp xếp Top hoặc Latest | không |
| lookup | Tìm web / tin tức (topic=news, timeframe day/week/month/year) | không |
| fetch | Đọc toàn văn một URL | không |
| format | Gom kết quả thành bản tin markdown (brief, sections, thread…) | không |
| send | Gửi bản tin lên Telegram — chỉ khi user đã xác nhận | không |
| policy | Tra chính sách nội bộ công ty (nguồn, dữ liệu, đăng bài) | không |
| papers / paper_text | Tìm paper arXiv / đọc text của một paper | không |
| **wiki** | Kiến thức nền từ Wikipedia (vi/en): định nghĩa, tiểu sử | **có** |
| **hn_search** | Bài đăng Hacker News, sắp xếp theo liên quan hoặc mới nhất | **có** |
| **github_repos** | Repo mã nguồn mở trên GitHub, theo số sao hoặc mới cập nhật | **có** |
| **hf_models** | Model trên Hugging Face, theo lượt tải hoặc lượt thích | **có** |

4 tool mới không cần API key, có `TOOL.md`, đăng ký trong `tools/__init__.py` + `tools.yaml`, mỗi tool có 3–4 unit test.

## A3. Câu hỏi mẫu để thử

1. Tin tức AI hôm nay có gì nổi bật?
2. Lấy 3 tweet mới nhất của Andrej Karpathy
3. Transformer trong học máy là gì?
4. Trên Hacker News gần đây mọi người bàn gì về AI agents?
5. Tìm 3 repo agent framework nhiều sao nhất trên GitHub
6. Thử "bẫy": *Tóm tắt bài này giúp mình* (agent phải hỏi lại URL) · *Đăng bản tin lên Telegram* (agent phải xin xác nhận) · *Giải tích phân x^2* (agent từ chối)

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Fill from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | baseline | - | - | 0.55 | runs/v0_B_base_gemini_20261110T102458997850.json |
| v1 | system_prompt.md: scope and clarification guardrails | Scope rules reduce out-of-scope and guessed tool calls | 0.55 | 0.85 | runs/v1_B_base_gemini_20261110T103824621286.json |
| v2 | tools.yaml: lookup contract | Structured news/date filters keep generic terms out of query | 0.85 | 0.95 | runs/v2_B_base_gemini_20261110T104822232162.json |
| v3 | system_prompt.md: send confirmation boundary | Explicit yes/no confirmation prevents sending before approval | 0.95 | 1.00 | runs/v3_B_base_gemini_20261110T105013460006.json |

## B2. Failure Analysis

Use actual failures from `results[*].result.failures`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R03_web_news_routing | wrong_tool | lookup(topic="news", timeframe="day", query="AI news") | Query thừa chữ "news" | v2: quy ước query trong tools.yaml |
| R08_out_of_scope | out_of_scope | send(confirmed=true) | Gọi send cho bài toán tích phân | v1: thêm Scope, bỏ "luôn gọi tool" |
| R09_no_tool_capability | unnecessary_tool | policy(query="nhiệm vụ và khả năng của trợ lý") | Gọi tool khi chỉ hỏi năng lực | v1: trả lời trực tiếp |
| R10_missing_handle | missing_info | timeline(screenname="sama", limit=5) | Đoán handle thay vì clarify | v1: bỏ chỉ dẫn "đoán" |
| R11_missing_url | missing_info | fetch(url="https://openai.com/index/learning-to-reason-with-llms/") | Dùng URL tự đoán thay vì clarify | v1: bỏ chỉ dẫn "đoán" |
| R12_confirm_before_send | wrong_boundary | send(confirmed=true) | Gọi send ngay, không xác nhận với người dùng | v1: bắt buộc clarify yes_no |
| R13_parallel_web_and_tweets | wrong_tool | lookup(topic="news", timeframe="day", query="latest AI news today") | Chỉ gọi lookup, thiếu social_search | v1: bỏ "một bước" |
| R14_out_of_scope_coding | out_of_scope | policy(query="tool usage code generation") | Gọi tool cho yêu cầu viết code | v1: thêm Scope |
| M02_carryover_timeframe | wrong_arg_value | lookup(topic="news", timeframe="day", query="robotics news") | Query thừa chữ "news" | v2: quy ước query |
| v1 / R03_web_news_routing | wrong_tool | lookup(query="AI news artificial intelligence OpenAI Google Anthropic", topic="news", timeframe="day") | Tự mở rộng query ngoài chủ đề người dùng nêu | v2: giữ query là chủ đề cốt lõi |
| v1 / R13_parallel_web_and_tweets | wrong_tool | lookup(query="AI news artificial intelligence", topic="news", timeframe="day"); social_search(query="AI") | Query web thừa cụm từ không yêu cầu | v2: quy ước query trong tools.yaml |
| v1 / M02_carryover_timeframe | wrong_arg_value | lookup(query="robotics news", topic="news", timeframe="day"); social_search(query="robotics") | Thêm "news" vào query và gọi dư social_search | v2: phân biệt bộ lọc với query |
| v2 / R12_confirm_before_send | wrong_boundary | clarify(response_type="text") | Hỏi bổ sung nội dung thay vì xác nhận yes/no trước khi gửi | v3: bắt buộc xác nhận yes_no trước |

## B3. Team Eval Cases

List the 10 cases added to `data/eval_group.json` (5 single turn + 5 multi turn).

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
|  |  |  |  |

## B4. Live Chat Evidence

Use `transcripts/*.transcript.json`.

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Bonus Evidence

Only fill if your team did bonus.

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| send (Telegram) | (transcript chat live) | Prompt v3 + description bắt buộc `clarify(yes_no)` trước, chỉ `send(confirmed=true)` sau khi user đồng ý | Code `send` tự chặn khi `confirmed=false` (test `test_send_without_confirmation_does_not_call_network`) |
| arXiv/company policy | (run extension) | Description `policy` map rõ `policy_area`; `papers` vs `paper_text` tách theo có/không có ID | Dòng chỉ dẫn lạ trong file policy bị đẩy vào `untrusted_text` (test `test_policy_instruction_like_lines_go_to_untrusted_text`) |
| UI | `app.py`, `transcripts/*_ui_*.transcript.json` | Streamlit dùng lại vòng lặp tool của `chat.py`, hiện tool call + args + kết quả, có nút câu hỏi mẫu, tự lưu transcript | Link Cloudflare tạm thời; key chỉ nằm trong `.env` trên máy chạy |
| 4 tool mới | `tools/wiki`, `tools/hn_search`, `tools/github_repos`, `tools/hf_models` | API công khai, không cần key; cùng format `items` nên dùng chung `format` | Query rỗng / enum sai trả error dict, không gọi mạng; `limit` ép kiểu và giới hạn 1–20 |
| Tool unit tests (`tests/`) | `pytest -q` → 96 passed, 0 skipped (116 sau khi áp `tools_v4.yaml`) | Điền hết stub TODO + 15 test cho 4 tool mới + 2 regression test | Mọi HTTP bị chặn và mock bằng `fake_http`, chạy offline, không tốn credit |

Tool unit tests: số test đã viết, số bug tìm được trong tool có sẵn (nếu có), và một ví dụ lỗi mà unit test bắt được nhưng eval không bắt được.

**Bug tìm được trong tool có sẵn (đã sửa, có regression test):**

1. `timeline` / `social_search` với `limit=-1` trả về *tất cả trừ phần tử cuối* (do cắt mảng `items[:-1]`). Sửa: ép `limit` về khoảng 1–20. Test: `test_timeline_negative_limit_still_returns_at_least_one`.
2. `fetch` với `url=""` vẫn POST lên Firecrawl và tốn 1 credit. Sửa: kiểm tra URL phải bắt đầu bằng `http://`/`https://`, sai thì trả error dict không gọi mạng. Test: `test_fetch_empty_url_returns_error_without_request`.

Ví dụ eval không bắt được: nếu model gọi `fetch(url="")` thì eval chỉ chấm sai args, nhưng không thấy được rằng tool đã đốt credit thật — chỉ unit test (assert `calls == []`) mới bắt được.

## B6. Reflection

- Which fixes belonged in `system_prompt.md`?
- Which fixes belonged in `tools.yaml`?
- Which failure needed manual review instead of automatic grading?
- What would you improve next?

## B7. Small Local Model Challenge (bonus)

Only fill if your team did the local model challenge.

| Version | Model (provider) | Prompt/Tools | case_accuracy | tool_routing | argument | multiturn | Run File |
|---|---|---|---|---|---|---|---|
| v3 | (cloud) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v4-local |  |  |  |  |  |  |  |
| v5-local |  |  |  |  |  |  |  |

Lỗi đặc thù của model nhỏ (đếm từ run JSON):

| Failure Pattern | Count | Example Case | Fix Tried | Helped? |
|---|---|---|---|---|
| wrong / hallucinated tool |  |  |  |  |
| invalid JSON args (`_invalid_json_arguments`) |  |  |  |  |
| no tool call / answered directly |  |  |  |  |
| missed `clarify` |  |  |  |  |
| repeated / unnecessary calls |  |  |  |  |

- Cái gì giúp model nhỏ gọi tool đúng hơn nhất? Bằng chứng?
- Bản prompt tối ưu cho local chạy trên model cloud thì sao?
- Khi nào nhóm sẽ chọn model local thay vì cloud cho agent này?
