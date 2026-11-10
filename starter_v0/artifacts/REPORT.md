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

Kết quả eval cố định (20 case, Gemini): **v0 55% → v1 85% → v2 95% → v3 100% → v4 100%**; 10 case nhóm ở v4: **10/10**.

**Link dùng thử (deploy):**

> Demo chạy local: `streamlit run app.py` → http://localhost:8501 (có thể public tạm bằng `cloudflared tunnel --url http://localhost:8501`).
>
> UI có 2 màn hình: **💬 Trò chuyện** (thanh công cụ bấm để thử, hiện tiến trình gọi công cụ trực tiếp, nút xác nhận Có/Không) và **🧰 Bộ công cụ** (thẻ cho từng công cụ kèm trạng thái API key, chạy thử từng công cụ mà không cần LLM).

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
| **post** | Đăng bài lên X (dry-run, ≤ 280 ký tự), phải xác nhận | **có** (safety) |
| **email** | Gửi email (dry-run), kiểm tra địa chỉ + xác nhận | **có** (safety) |
| **share_doc** | Chia sẻ tài liệu nội bộ (dry-run), kiểm tra policy + xác nhận | **có** (safety) |

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
| v4 | tools.yaml: viết lại toàn bộ description (làm gì / khi nào dùng / khi nào KHÔNG dùng / quy ước args) + khai báo 4 tool mới | Description rõ ràng giữ base 100% và route đúng 4 tool mới | 1.00 | 1.00 (group 10/10) | runs/v4_B_base_gemini_20261110T110932624064.json · runs/v4_B_group_gemini_20261110T110912651656.json |

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
| G01_wiki_concept_routing | Câu hỏi định nghĩa route tới `wiki` (lang=vi), không phải `lookup` | `wiki(lang="vi")` | PASS · `wiki(query="Transformer", lang="vi", limit=3)` |
| G02_hn_latest_sort | Route tới `hn_search`; "gần đây" → sort=date | `hn_search(sort="date")` | PASS · `hn_search(query="AI agents", sort="date", limit=5)` |
| G03_github_most_stars | Route tới `github_repos`; "nhiều sao nhất" → stars, "3 repo" → limit=3 | `github_repos(sort="stars", limit=3)` | PASS · `github_repos(query="agent framework", sort="stars", limit=3)` |
| G04_hf_most_liked | Route tới `hf_models`; "được thích nhiều nhất" → sort=likes | `hf_models(sort="likes")` | PASS · `hf_models(query="vietnamese", sort="likes", limit=5)` |
| G05_handle_strip_at | Bỏ ký tự @ khỏi handle, giữ limit=3 | `timeline(screenname="karpathy", limit=3)` | PASS · `timeline(screenname="karpathy", limit=3)` |
| G06_send_after_explicit_confirm (multi) | User đã xác nhận ở lượt cuối → gọi send confirmed=true | `send(confirmed=true)` | PASS · `send(text="AI hôm nay - OpenAI ra mắt model mới", confirmed=true)` |
| G07_send_not_yet_confirmed (multi) | Yêu cầu gửi ở lượt sau vẫn chưa phải xác nhận | `clarify(response_type="yes_no")` | PASS · `clarify(response_type="yes_no")` |
| G08_clarify_then_hn (multi) | Gom 3 lượt: nền tảng HN + chủ đề LLM + "mới nhất" | `hn_search(query="LLM", sort="date")` | PASS · `hn_search(query="LLM", sort="date")` |
| G09_switch_hf_to_github (multi) | User đổi từ hf_models sang github_repos, giữ chủ đề whisper | `github_repos(query="whisper")` | PASS · `github_repos(query="whisper")` |
| G10_out_of_scope_after_research (multi) | Lượt cuối ngoài phạm vi → không gọi tool dù lượt trước là research | no_tool, từ chối | PASS · không gọi tool |

Kết quả: **10/10 PASS** (routing 1.0, args 1.0, multiturn 1.0) — `runs/v4_B_group_gemini_20261110T110912651656.json`.

## B4. Live Chat Evidence

Use `transcripts/*.transcript.json`.

Tất cả transcript chạy qua UI Streamlit (`source: streamlit_ui`), artifact `v3+p06351cad3849+tf03e40ed643b` — tức prompt v3 + `tools.yaml` v4 (cùng tools hash `f03e40…` với run v4; nhãn "v3" là nhãn version mặc định của UI lúc đó).

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
| 1 | Tin tức AI hôm nay có gì nổi bật? | `lookup(query="AI", topic="news", timeframe="day")` → `format(template="daily_ai_vn")` | `transcripts/v3_gemini_ui_20261110T123739322421.transcript.json` | ✅ Bản tin AI chia theo mục, có nguồn |
| 2 | Mọi người trên Twitter đang bàn gì về GPT-5? | `social_search(query="GPT-5")` + `lookup(query="GPT-5")` | cùng file trên | ⚠️ API Twitter lỗi → agent báo lỗi thật, chuyển sang nguồn web, không bịa tweet |
| 3 | Lấy 3 tweet mới nhất của Andrej Karpathy | `timeline(screenname="karpathy", limit=3)` | `transcripts/v3_gemini_ui_20261110T124431363621.transcript.json` | ⚠️ Thiếu key RapidAPI → agent nói rõ không lấy được, không bịa |
| 4 | Tìm 3 repo agent framework nhiều sao nhất trên GitHub | `github_repos(query="agent framework", sort="stars", limit=3)` | cùng file trên | ✅ Tool mới, đúng args |
| 5 | Transformer trong học máy là gì? | `wiki(query="Transformer", lang="vi", limit=3)` | `transcripts/v3_gemini_ui_20261110T123111995423.transcript.json` | ✅ Tool mới `wiki` |
| 6 | Trên Hacker News gần đây mọi người bàn gì về AI agents? | `hn_search(query="AI agents", sort="date", limit=5)` | `transcripts/v3_gemini_ui_20261110T122914399170.transcript.json` | ✅ Tool mới, "gần đây" → sort=date |
| 7 | 2 cộng 3 | (không gọi tool) | `transcripts/v3_gemini_ui_20261110T124614829845.transcript.json` | ✅ Từ chối, ngoài phạm vi research |
| 8 | tin tức mới nhất ngày mai → "công nghệ" | `clarify(response_type="text")` → `lookup(query="công nghệ", topic="news", timeframe="day")` | cùng file trên | ✅ Hỏi lại chủ đề rồi mới tìm (multi-turn) |
| 9 | lấy 5 repo nhiều sau trên github | `github_repos(query="stars:>100000", sort="stars", limit=5)` | cùng file trên | ✅ Hiểu lỗi chính tả "sau" = sao, limit=5 |

## B5. Bonus Evidence

Only fill if your team did bonus.

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| send (Telegram) | (transcript chat live) | Prompt v3 + description bắt buộc `clarify(yes_no)` trước, chỉ `send(confirmed=true)` sau khi user đồng ý | Code `send` tự chặn khi `confirmed=false` (test `test_send_without_confirmation_does_not_call_network`) |
| arXiv/company policy | (run extension) | Description `policy` map rõ `policy_area`; `papers` vs `paper_text` tách theo có/không có ID | Dòng chỉ dẫn lạ trong file policy bị đẩy vào `untrusted_text` (test `test_policy_instruction_like_lines_go_to_untrusted_text`) |
| UI | `app.py`, `transcripts/*_ui_*.transcript.json` | Streamlit dùng lại vòng lặp tool của `chat.py` (thêm callback `on_event`), tên công cụ tiếng Việt dễ hiểu, tiến trình gọi công cụ trực tiếp, nút Có/Không khi agent xin xác nhận, trang Bộ công cụ chạy thử từng công cụ không cần LLM, tự lưu transcript | Link Cloudflare tạm thời; key chỉ nằm trong `.env` trên máy chạy |
| 4 tool mới | `tools/wiki`, `tools/hn_search`, `tools/github_repos`, `tools/hf_models` | API công khai, không cần key; cùng format `items` nên dùng chung `format` | Query rỗng / enum sai trả error dict, không gọi mạng; `limit` ép kiểu và giới hạn 1–20 |
| Tool unit tests (`tests/`) | `pytest -q` → 131 passed, 0 skipped (gồm test cho 4 tool mới + 3 safety tool) | Điền hết stub TODO + 15 test cho 4 tool mới + 2 regression test | Mọi HTTP bị chặn và mock bằng `fake_http`, chạy offline, không tốn credit |

Tool unit tests: số test đã viết, số bug tìm được trong tool có sẵn (nếu có), và một ví dụ lỗi mà unit test bắt được nhưng eval không bắt được.

**Bug tìm được trong tool có sẵn (đã sửa, có regression test):**

1. `timeline` / `social_search` với `limit=-1` trả về *tất cả trừ phần tử cuối* (do cắt mảng `items[:-1]`). Sửa: ép `limit` về khoảng 1–20. Test: `test_timeline_negative_limit_still_returns_at_least_one`.
2. `fetch` với `url=""` vẫn POST lên Firecrawl và tốn 1 credit. Sửa: kiểm tra URL phải bắt đầu bằng `http://`/`https://`, sai thì trả error dict không gọi mạng. Test: `test_fetch_empty_url_returns_error_without_request`.

Ví dụ eval không bắt được: nếu model gọi `fetch(url="")` thì eval chỉ chấm sai args, nhưng không thấy được rằng tool đã đốt credit thật — chỉ unit test (assert `calls == []`) mới bắt được.

## B6. Reflection

- **Which fixes belonged in `system_prompt.md`?** Ranh giới hành vi: phạm vi (từ chối toán/viết code, không gọi tool khi chỉ hỏi năng lực), "thiếu thông tin thì hỏi lại, không đoán" (R10, R11), và xác nhận yes/no trước khi gửi (R12). v1 là thay đổi tăng điểm nhiều nhất: **55% → 85% (+30 điểm)**; v3 sửa R12: 95% → 100%.
- **Which fixes belonged in `tools.yaml`?** Hợp đồng tham số và routing giữa các tool chồng chéo: quy ước `lookup.query` chỉ chứa chủ đề, ý "tin tức"/thời gian đi vào `topic`/`timeframe` (R03, M02: v2 85% → 95%); v4 viết lại mọi description theo mẫu *làm gì / khi nào dùng / khi nào KHÔNG dùng / quy ước args* để route đúng 4 tool mới (group 10/10) mà base vẫn giữ 100%.
- **Which failure needed manual review instead of automatic grading?** R12 không ổn định: PASS ở v1 rồi FAIL ở v2 dù prompt không đổi (cùng hash `a606…`) — phải đọc run JSON mới thấy model hỏi lại nội dung (`response_type="text"`) thay vì xin xác nhận. Trong chat live, khi API Twitter lỗi/thiếu key, eval không chấm được, phải đọc transcript để xác nhận agent báo lỗi thật chứ không bịa tweet.
- **Unit test bắt được gì mà eval không bắt được?** `fetch(url="")` vẫn gọi Firecrawl và tốn credit; `timeline(limit=-1)` cắt sai mảng. Eval chỉ nhìn tool call + args nên không thấy, unit test với `fake_http` (assert không có request) mới bắt được.
- **What would you improve next?** Chạy mỗi version 2–3 lần để đo độ ổn định thay vì 1 lần; thêm case group cho 3 safety tool (`post`, `email`, `share_doc`) và log thành v5; thêm case cho tình huống tool trả lỗi (API down) để chấm việc agent không bịa kết quả.

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
