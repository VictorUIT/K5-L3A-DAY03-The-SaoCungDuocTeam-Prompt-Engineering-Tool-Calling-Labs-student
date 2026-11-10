# Day 03 Lab v2 — Research Agent Tool Eval

## Brief

Trong lab này, nhóm build một research agent nhỏ nhưng chạy thật. Agent nhận request của user, chọn tool, truyền arguments, chạy tool thật, lưu full JSON log, rồi dùng log đó để tối ưu prompt/tool declaration qua nhiều version.

Điều cần học không phải là "chatbot trả lời hay". Điều cần học là vòng lặp evidence-driven:

1. Chạy baseline bằng API thật.
2. Đọc run JSON để biết sai tool, sai args, thiếu hỏi lại, hoặc gọi tool thừa.
3. Sửa `artifacts/system_prompt.md` hoặc `artifacts/tools.yaml`.
4. Chạy lại và ghi versioning.
5. Tự viết thêm eval case để đo những lỗi nhóm quan tâm.
6. Viết report dựa trên log thật, không dựa vào cảm giác.

## Scope

Nhiệm vụ bắt buộc:

- Setup chạy được bằng provider thật.
- Agent có ít nhất 5 tool trong `artifacts/tools.yaml`.
- Chạy base eval.
- Tối ưu ít nhất 3 vòng sau baseline: `v1`, `v2`, `v3`.
- Ghi `artifacts/version_log.csv`.
- Viết thêm ít nhất 1 tool mới (kèm `TOOL.md`, đăng ký trong `tools/__init__.py` và `tools.yaml`).
- Viết unit test cho tool mới (≥ 3 test/tool) và giữ `pytest` xanh — xem [Step 4b](#step-4b--challenge-viết-test-cho-tool).
- Tự viết thêm 10 eval case vào `data/eval_group.json`, trong đó 5 single turn và 5 multi turn.
- Nộp run JSON, transcript JSON, report.
- Bắt buộc có UI chạy được bằng Streamlit hoặc Vercel.
- Hoàn thành `artifacts/REPORT.md`: Phần A (giới thiệu agent: tool gì, làm được gì, câu hỏi mẫu) xong **trước 16:30** làm tài liệu phụ trợ khi demo; Phần B (chi tiết) hoàn thiện sau để nộp bài.

Bonus:

- Action tool `send`: có confirmation trước khi gửi.
- Extra tools: `policy`, `papers`, `paper_text`.
- **Small Local Model Challenge**: chạy agent bằng model local nhỏ (≤ 8B) qua Ollama — xem [Step 7](#step-7--bonus-challenge-small-local-model).


**Điểm thưởng (bonus point):** team nào làm **CẢ HAI** — dựng được UI **và** tự viết thêm hơn 3 tool mới (ngoài các tool có sẵn, kèm `TOOL.md` + đăng ký trong `tools/__init__.py` + `tools.yaml`) — sẽ được cộng điểm thưởng.

## TODO Checklist

Đánh dấu khi xong. Mỗi dòng trỏ tới file cần sửa và bằng chứng cần nộp.

**Setup**
- [ ] `.env` có provider key + `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, `RAPIDAPI_KEY`
- [ ] `python scripts/preflight_provider.py --provider openrouter` pass
- [ ] `pytest` chạy được: contract test + example test xanh, TODO test đang `skipped`

**Prompt & tool declaration**
- [ ] Chạy baseline `v0`, ghi vào `artifacts/version_log.csv`
- [ ] Liệt kê các case FAIL của `v0` và gán mỗi case một loại lỗi (`wrong_tool`, `wrong_arg_value`, `missing_info`...)
- [ ] `artifacts/system_prompt.md`: bỏ các chỉ dẫn xấu cố ý của starter (đoán thay vì hỏi, gửi không cần xác nhận, ép một bước)
- [ ] `artifacts/system_prompt.md`: thêm rule routing (khi nào `timeline` / `social_search` / `lookup` / `fetch` / `clarify`)
- [ ] `artifacts/tools.yaml`: viết lại `description` mỗi tool: làm gì, **khi nào dùng / khi nào không dùng**
- [ ] `artifacts/tools.yaml`: mô tả rõ convention args (handle không có `@`, `topic=news` cho tin tức, `timeframe`, `search_type=Top|Latest`)
- [ ] `artifacts/tools.yaml`: `send` mô tả rõ chỉ gửi khi user đã xác nhận (`confirmed=true`)
- [ ] `v1`, `v2`, `v3`: mỗi version **một** giả thuyết, metric trước/sau trong `version_log.csv`

**Tool mới**
- [ ] `tools/<tên>/tool.py` + `TOOL.md` (frontmatter đúng contract trong `tools/README.md`)
- [ ] Đăng ký trong `tools/__init__.py` (`TOOL_FUNCTIONS`) và `artifacts/tools.yaml`
- [ ] Unit test cho tool mới trong `tests/test_tools_todo.py` (≥ 3 test)
- [ ] Ít nhất 1 eval case trong `data/eval_group.json` kiểm tra model có route tới tool mới đúng lúc

**Testing**
- [ ] `data/eval_group.json`: case cho model (routing / args / boundary), xem Step 4
- [ ] `tests/test_tools_todo.py`: unit test cho code của tool, xem Step 4b
- [ ] `pytest`: 0 failed, 0 skipped

**Demo & report**
- [ ] UI chạy được + link dùng thử
- [ ] `chat.py`: ≥ 3 lượt live, có transcript
- [ ] `artifacts/REPORT.md` Phần A trước 16:30, Phần B trước khi nộp

**Bonus (tuỳ chọn)**
- [ ] `send` có xác nhận trước khi gửi, có transcript chứng minh
- [ ] Small Local Model Challenge (Step 7)

## Folder Map

```text
starter_v0/
  agent.py                    # one-shot model -> tool calls -> tool execution
  chat.py                     # interactive chat, multi-round tools, transcript JSON
  run_eval.py                 # eval routing + args, writes runs/*.json
  versioning.py               # prompt/tool hash
  pytest.ini
  tests/
    conftest.py               # offline fixtures: block real network, fake_http, clean env
    test_tool_contract.py     # tools.yaml <-> code <-> eval stay in sync (given, keep green)
    test_tools_examples.py    # worked examples to copy
    test_tools_todo.py        # TODO(student): tool unit test challenge
  artifacts/
    system_prompt.md          # student edits
    tools.yaml                # student edits
    version_log.csv           # student fills
    REPORT.md                 # report: Phần A debate poster + Phần B chi tiết
  data/
    eval_base.json            # fixed base eval, do not edit the cases
    eval_group.json           # team adds at least 5 cases
    eval_research_extension.json
  tools/
    README.md                 # tool folder contract
    <tool_name>/
      TOOL.md                 # frontmatter + notes
      tool.py                 # self-contained implementation
  company_policy/             # local markdown KB for bonus policy tool
  providers/                  # OpenRouter/OpenAI/Anthropic/Gemini/Ollama (local) adapters
  scripts/preflight_provider.py
  samples/                    # mock format examples (transcript, run-analysis, version_log)
```

## Tool Tracks

Phần mô tả dưới đây tóm tắt mỗi tool *làm gì*. Việc xác định *khi nào dùng* tool nào là phần nhóm tự định nghĩa trong prompt và tool declaration.

Core tools:

- `clarify`: gửi một câu hỏi cho người dùng và chờ lượt trả lời tiếp theo.
- `timeline`: lấy bài đăng gần đây của một tài khoản (`screenname`).
- `social_search`: tìm bài đăng theo từ khóa (`search_type`: Latest/Top).
- `lookup`: tìm trên web (có `topic` general/news và `timeframe`).
- `fetch`: đọc nội dung một URL.
- `format`: trình bày các item đã có thành markdown digest.

Bonus tools:

- `send`: gửi text lên Telegram channel (chỉ gửi khi `confirmed=true`).
- `policy`: tìm trong company policy markdown nội bộ.
- `papers`: tìm paper trên arXiv.
- `paper_text`: tải PDF arXiv và trích text cục bộ.

Mỗi tool nằm trong thư mục riêng dưới `starter_v0/tools/<tool_name>/`.

## ⚠️ Nếu nhóm đổi tên tool: phải đồng bộ

Eval chấm theo **đúng tên tool**. Nếu nhóm đổi tên một tool cho rõ nghĩa hơn (ví dụ `send` → `send_telegram`), **phải đổi đồng bộ ở CẢ những nơi sau**, nếu không eval báo lỗi `not declared in tools.yaml` hoặc chấm sai mọi case:

1. `artifacts/tools.yaml` — field `name`
2. `tools/__init__.py` — key trong `TOOL_FUNCTIONS`
3. `data/eval_base.json` **và** `data/eval_research_extension.json` — `expect.tool_calls[].name`

(Không cần đổi tên hàm trong `tools/<folder>/tool.py` — chỉ cần key trỏ đúng hàm. Không sửa *nội dung case* trong `eval_base.json`, chỉ đổi tên tool nếu nhóm rename.)

## Setup

Run from `starter_v0/`:

```bash
cd starter_v0
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env`. Minimum recommended:

```bash
OPENROUTER_API_KEY=...
TAVILY_API_KEY=...
FIRECRAWL_API_KEY=...
RAPIDAPI_KEY=...
RAPIDAPI_TWITTER_HOST=twitter-api45.p.rapidapi.com
```

Tool setup details are in [TOOL-SETUP.md](TOOL-SETUP.md).

Preflight:

```bash
python scripts/preflight_provider.py --provider openrouter
```

If preflight fails, fix provider key, dependency, or network before running eval.

## Step 1 — Run Baseline

Run the fixed base eval as `v0`:

```bash
python run_eval.py \
  --provider openrouter \
  --version v0 \
  --suite base \
  --eval-cases data/eval_base.json
```

Output is saved to `runs/*.json`. Read:

- `summary.case_accuracy`
- `summary.tool_routing_accuracy`
- `summary.argument_accuracy`
- `summary.multiturn_accuracy`
- `results[*].result.failures`
- `results[*].result.observed_mismatch`

The run JSON also stores `artifact_version`, `prompt_hash`, `tools_hash`, actual tool calls, and actual tool results. That is the evidence for your report.

Optional: parse run JSON into a flat CSV table for analysis:

```bash
python scripts/parse_runs.py runs/ --output analysis/base_runs.csv
```

## Step 2 — Fix One Thing

Edit only:

- `artifacts/system_prompt.md`
- `artifacts/tools.yaml`

Do not edit the cases in `data/eval_base.json`.

Method, not memorized answers:

1. Mở run JSON. Với mỗi case FAIL, đọc `observed_mismatch` + `failures` + `actual_tool_calls`.
2. Đặt một giả thuyết: *vì sao* agent chọn sai (thiếu rule routing? thiếu convention args? prompt đang khuyến khích đoán/gửi/làm-một-bước?).
3. Sửa **một** thứ (một dòng prompt hoặc một description) để kiểm chứng giả thuyết đó.
4. Chạy lại, so metric trước/sau. Nếu không cải thiện, đổi giả thuyết.

Đổi một giả thuyết mỗi lần để version log có ý nghĩa.

## Step 3 — Run 3 Optimization Versions

Run at least three improved versions:

```bash
python run_eval.py --provider openrouter --version v1 --suite base --eval-cases data/eval_base.json
python run_eval.py --provider openrouter --version v2 --suite base --eval-cases data/eval_base.json
python run_eval.py --provider openrouter --version v3 --suite base --eval-cases data/eval_base.json
```

After each run, fill `artifacts/version_log.csv`:

```text
version,author,changed_artifact,artifact_version,prompt_hash,tools_hash,reason,hypothesis,metric_before,metric_after,run_file
```

Use hashes and run file paths from the eval output.

## Step 4 — Add Team Eval

Add at least 5 cases to `data/eval_group.json`.

Each case needs:

- `id`
- `phase`: always `"B"`
- `query` or `turns`
- `failure_type`: one of `wrong_tool`, `wrong_arg_value`, `wrong_boundary`, `unnecessary_tool`, `out_of_scope`, `missing_info`
- `expect`: `tool_calls` or `no_tool`
- `metadata.what_it_tests`

Run:

```bash
python run_eval.py \
  --provider openrouter \
  --version v3 \
  --suite group \
  --eval-cases data/eval_group.json
```

Optional extension eval:

```bash
python run_eval.py \
  --provider openrouter \
  --version v3 \
  --suite extension \
  --eval-cases data/eval_research_extension.json
```

## Step 4b — Challenge: Viết test cho tool

Eval ở Step 4 đo **model** (chọn tool và args có đúng không). Unit test ở đây đo **code của tool** (nhận args đó thì có chạy đúng không). Hai loại lỗi này khác nhau: model gọi đúng `lookup(topic="news")` nhưng tool quên gửi `topic` lên API thì eval vẫn báo PASS, còn user vẫn nhận kết quả sai.

```bash
pytest              # toàn bộ suite, offline, không tốn credit API
pytest -v tests/test_tools_todo.py
```

Có sẵn:

- `tests/test_tool_contract.py`: kiểm tra `tools.yaml` khớp với code. Mỗi tool khai báo phải có implementation, mọi param khai báo phải có trong signature hàm, có `TOOL.md` đúng tên, eval chỉ dùng tool đã khai báo. Test này phải luôn xanh, chạy lại mỗi khi rename hay thêm tool.
- `tests/test_tools_examples.py`: 5 mẫu để copy: tool local thuần, guardrail (`send` không gửi khi chưa xác nhận), mock HTTP cho tool gọi API, nhánh lỗi (thiếu key, HTTP 429), và test vòng lặp agent bằng fake provider không cần model.
- `tests/conftest.py`: mọi HTTP thật đều bị chặn, phải mock bằng fixture `fake_http`. Các env key bị xoá trước mỗi test.

Nhiệm vụ:

1. **Bắt buộc:** viết ≥ 3 test cho mỗi tool mới của nhóm (happy path; input xấu từ model như chuỗi rỗng, sai kiểu, ngoài enum; nhánh lỗi trả error dict chứ không raise).
2. **Challenge:** điền hết các stub `pytest.skip(TODO)` trong `tests/test_tools_todo.py` (clarify, format, send, lookup, fetch, timeline, social_search, policy). Đạt khi `pytest` báo **0 failed, 0 skipped**.
3. **Challenge+:** nếu test phát hiện bug trong tool có sẵn, ghi lại bug đó, sửa nó, và giữ lại test đã bắt được bug (regression test). Ghi vào REPORT B5. Gợi ý: thử input biên mà model hay gửi, như `limit=0`, `top_k=0`, số dạng chuỗi (`max_results="5"`), `items` thiếu `url`, rồi tự quyết định hành vi hiện tại có đúng mong đợi không.

Nguyên tắc: một test kiểm tra một hành vi, tên test mô tả hành vi đó (`test_send_without_confirmation_does_not_call_network`), và assert cả **request gửi đi** lẫn **kết quả trả về**.

## Step 5 — Chat Live

`chat.py` is for live multi-round interaction. It logs every turn to `transcripts/*.transcript.json`.

```bash
python chat.py --provider openrouter --version v3
```

Try at least 3 live turns, for example:

- A normal research request.
- A request thiếu thông tin (không nói rõ account/URL), rồi lượt sau bổ sung.
- Một request "đăng/gửi bản tin lên Telegram" — quan sát agent có hành động ngay hay hỏi lại trước, rồi tự quyết định hành vi nào mới đúng và sửa prompt cho khớp.

## Deploy nhanh để team khác dùng thử (khuyến nghị: Cloudflare Tunnel)

Để team cùng zone tự thử agent trong Team showdown, expose UI đang chạy local ra một link public. Cách nhanh nhất, không cần đăng ký domain hay deploy lên cloud, là **Cloudflare Tunnel** (`cloudflared`).

1. Chạy UI local trước (ví dụ Streamlit mặc định cổng `8501`):

   ```bash
   streamlit run app.py            # → http://localhost:8501
   ```

2. Cài `cloudflared`:

   ```bash
   brew install cloudflared                          # macOS
   winget install --id Cloudflare.cloudflared        # Windows (hoặc: scoop install cloudflared)
   # Linux: xem https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
   ```

   Windows: nếu báo `cloudflared not recognized`, mở terminal mới rồi chạy lại.

3. Mở tunnel trỏ vào cổng UI — lệnh trả về ngay một URL `https://<random>.trycloudflare.com`:

   ```bash
   cloudflared tunnel --url http://localhost:8501
   ```

4. Copy URL đó, dán vào `REPORT.md` Phần A (mục "Link dùng thử") để team khác mở thử.

Lưu ý: link `trycloudflare.com` là tạm thời, sống theo phiên `cloudflared` (tắt lệnh là mất). Giữ lệnh chạy trong suốt buổi showdown. Nếu team deploy hẳn lên Vercel/Streamlit Cloud thì dùng link đó thay cho tunnel.

## Deploy chatbot trên Vercel

Repo có thể deploy giao diện HTML và API Python cùng một Vercel project:

1. Import repository trên Vercel và đặt **Root Directory** là thư mục gốc của repository (không phải `starter_v0/`).
2. Trong **Settings → Environment Variables**, thêm `OPENROUTER_API_KEY`. Có thể đặt `AGENT_PROVIDER=openrouter` (mặc định) và `AGENT_MODEL` nếu muốn chọn model khác. Nếu dùng tool cần dịch vụ ngoài, cấu hình thêm các key tương ứng như `TAVILY_API_KEY`, `FIRECRAWL_API_KEY` hoặc `RAPIDAPI_KEY`.
3. Deploy. Vercel nhận diện Flask app tại `app.py`, cài các package trong `requirements.txt`, và phục vụ giao diện từ `public/index.html`.

Không commit `.env` hoặc API keys. Mỗi request gửi tối đa 5 cặp hội thoại gần nhất từ trình duyệt; API không lưu session trong bộ nhớ serverless. Tải lại trang sẽ bắt đầu một phiên mới. `vercel.json` đặt thời lượng tối đa function là 60 giây, tùy giới hạn plan của Vercel.

API chat công khai có thể phát sinh chi phí từ provider. Trước khi chia sẻ rộng, hãy bật giới hạn chi tiêu/rate limit ở provider và cấu hình Vercel Deployment Protection hoặc bổ sung xác thực phù hợp.

Để chạy và kiểm tra theo cấu hình Vercel trên máy local, cài Vercel CLI rồi chạy `vercel dev` từ thư mục gốc.

## Step 6 — Report + Debate Poster

Hoàn thành `artifacts/REPORT.md`. File này có 2 phần với deadline khác nhau:

- **Phần A — Giới thiệu agent** (ngắn gọn 1 trang) — **phải xong trước 16:30**, làm tài liệu phụ trợ để team khác hiểu nhanh khi demo. Chỉ cần: (1) agent làm được gì, (2) agent có những tool gì và mỗi tool làm được gì, (3) vài câu hỏi mẫu để team khác tự thử.
- **Phần B — Chi tiết / Bằng chứng** — **có thể hoàn thiện sau Team showdown để nộp bài**. Bảng đầy đủ v0–v3, failure analysis, eval cases, live chat, reflection — dựa trên log thật (run JSON, version_log).

**Format Phần A:** nộp tối thiểu bản markdown trong `REPORT.md`. Khuyến khích biến Phần A thành **poster HTML/SVG 1 trang** để show trực tiếp cho team cùng zone (ví dụ `artifacts/poster.html` hoặc `artifacts/poster.svg`) — cùng nội dung, dễ nhìn hơn. Poster HTML/SVG là tùy chọn, không thay thế bản markdown.

## Step 7 — Bonus Challenge: Small Local Model

Câu hỏi: **prompt + tool declaration nhóm vừa tối ưu cho model cloud có còn đúng khi chạy model nhỏ trên máy mình không?** Model nhỏ (3B–8B) chạy offline, không tốn tiền, dữ liệu không rời máy, nhưng gọi tool kém hơn rõ: chọn sai tool, JSON arguments lỗi, bịa tool không có, gọi lặp, hoặc trả lời luôn thay vì gọi `clarify`. Bài này đo khoảng cách đó bằng log thật rồi tìm cách thu hẹp nó.

### Setup

1. Cài [Ollama](https://ollama.com/download) (`brew install ollama` trên macOS), rồi chạy `ollama serve` (app desktop tự chạy sẵn).
2. Kéo **ít nhất 2** model hỗ trợ tool calling, có kích thước khác nhau:

   ```bash
   ollama pull qwen2.5:7b      # mặc định của provider, ~4.7 GB
   ollama pull llama3.2:3b     # nhỏ hơn, ~2 GB
   # Gợi ý khác: qwen2.5:3b, llama3.1:8b, mistral:7b
   # Model phải có tag "tools" trên https://ollama.com/search?c=tools
   ```

   Máy yếu (RAM < 16 GB): dùng model 3B. Không cần API key; provider `ollama` gọi `http://localhost:11434/v1` (đổi bằng `OLLAMA_BASE_URL` nếu dùng LM Studio / llama.cpp server).

3. Preflight:

   ```bash
   python scripts/preflight_provider.py --provider ollama --model qwen2.5:7b
   ```

### Nhiệm vụ

1. **Baseline local:** chạy base eval với prompt/tools **v3** (bản tốt nhất của nhóm), không sửa gì, trên từng model local:

   ```bash
   python run_eval.py --provider ollama --model qwen2.5:7b  --version v3-qwen7b --suite base --eval-cases data/eval_base.json
   python run_eval.py --provider ollama --model llama3.2:3b --version v3-llama3b --suite base --eval-cases data/eval_base.json
   ```

2. **Phân loại lỗi:** đọc run JSON, đếm lỗi đặc thù của model nhỏ mà model cloud không mắc:
   - `wrong_tool` / bịa tên tool không có trong `tools.yaml`
   - arguments JSON lỗi: provider giữ lại raw text trong `args._invalid_json_arguments`, nên vẫn tính là lỗi arg, không biến thành `provider_error`
   - không gọi tool (trả text thay vì tool call), hoặc gọi tool khi lẽ ra phải `clarify`
   - gọi thừa / lặp cùng một tool

3. **Tối ưu cho model nhỏ:** ít nhất **2 vòng** (`v4-local`, `v5-local`), mỗi vòng một giả thuyết, như Step 2. Hướng gợi ý (không bắt buộc):
   - Rút gọn system prompt; model nhỏ dễ "lạc" với prompt dài.
   - Viết `description` của tool ngắn, cụ thể, có ví dụ args; bớt field optional.
   - Thêm 1–2 ví dụ few-shot routing trong prompt.
   - Bỏ tool không cần cho suite đang chạy để giảm nhiễu lựa chọn.

   Có thể dùng bản prompt/tools riêng cho local qua `--system-prompt` / `--tools` (ví dụ `artifacts/system_prompt_local.md`) để không phá bản v3 của model cloud.

4. **Kiểm tra ngược:** chạy lại bản `v5-local` trên model cloud. Điểm có giảm không? Có tìm được một bản prompt dùng tốt cho cả hai không?

5. Ghi mọi run vào `artifacts/version_log.csv` (ghi rõ model trong cột `reason` hoặc `version`), và điền mục **B7** trong `REPORT.md`.

Lưu ý: model local chậm hơn nhiều (vài giây đến vài chục giây mỗi case). Chạy thử 3–5 case trước bằng một file eval nhỏ nếu máy yếu. Ollama có thể bỏ qua `tool_choice="required"`, nên model local có thể không gọi tool ở case bắt buộc phải gọi; đó là một lỗi cần đo, không phải bug của harness.

**Tiêu chí đạt:** ≥ 2 model local đã chạy base eval, ≥ 2 vòng tối ưu có log, bảng so sánh cloud vs local trong REPORT, và ít nhất một kết luận có bằng chứng về việc "cái gì giúp model nhỏ gọi tool đúng hơn".

## Submit

Submit `starter_v0/` with:

- `artifacts/system_prompt.md`
- `artifacts/tools.yaml`
- `artifacts/version_log.csv` with at least `v0`, `v1`, `v2`, `v3`
- `artifacts/REPORT.md` (Phần A debate poster — xong trước 16:30; Phần B chi tiết — nộp sau)
- `artifacts/poster.html` hoặc `artifacts/poster.svg` nếu team làm poster để debate (tùy chọn)
- `data/eval_group.json` with at least 5 team cases
- `tests/` (unit test cho tool mới; nếu làm challenge thì `test_tools_todo.py` không còn `skip`)
- `runs/*.json`
- `analysis/*.csv` if you parsed run logs
- `transcripts/*.transcript.json`
- code changes if your team added or changed tools/UI
- nếu làm Small Local Model Challenge: run JSON của model local và prompt/tools riêng cho local (nếu có)

Do not submit `.env` or API keys.

## Checkpoint 4h

- 15:00 - Run baseline + build UI
- 15:30 - Improve prompt/tools for v1 + build at least 1 tool
- 16:00 - Write team eval cases + improve v2
- 16:30 - Team showdown (demo sản phẩm; REPORT.md Phần A / poster là tài liệu phụ trợ để team khác hiểu nhanh agent có tool gì, làm được gì)
- 17:30 - Improve v3 + hoàn thiện report Phần B
