# Hướng dẫn làm nốt Lab 03 (từ v3 đến nộp bài)

Mọi lệnh chạy trong Terminal của Mac, từ thư mục `~/Documents/lab03/starter_v0`, với `.venv` đã kích hoạt:

```bash
cd ~/Documents/lab03/starter_v0
source .venv/bin/activate
```

## Những gì đã có sẵn trong repo

| Phần | File | Trạng thái |
|---|---|---|
| v0, v1, v2, v3 | `runs/`, `artifacts/version_log.csv`, REPORT B1 | ✅ v0 55% → v1 85% → v2 95% → v3 100% |
| 4 tool mới (không cần API key) | `tools/wiki`, `tools/hn_search`, `tools/github_repos`, `tools/hf_models` | ✅ code + `TOOL.md` + đăng ký trong `tools/__init__.py` |
| Unit test | `tests/test_tools_todo.py` | ✅ hết stub TODO, ≥ 3 test/tool mới, 2 regression test |
| Sửa 2 bug tool có sẵn | `tools/timeline`, `tools/social_search`, `tools/fetch` | ✅ ghi vào REPORT B5 |
| `tools.yaml` viết lại toàn bộ + khai báo tool mới | `artifacts/tools_v4.yaml` | ⏳ dùng ở bước v4 |
| 10 eval case nhóm (5 single, 5 multi) | `data/eval_group.next.json` | ⏳ dùng ở bước v4 |
| UI Streamlit | `app.py` | ✅ chạy bằng `streamlit run app.py` |
| REPORT Phần A, Team, B5 | `artifacts/REPORT.md` | ✅ còn thiếu link dùng thử |

## Bước 0: cài thêm Streamlit và kiểm tra test

```bash
pip install -r requirements.txt
pytest -q
```

Kết quả mong đợi: `96 passed`, không có `skipped`.

## Bước 1: v3, chỉ đổi prompt (sửa R12) — ✅ ĐÃ XONG: 100%, đã ghi log

Ở v2, case R12 hỏi lại nội dung (`response_type="text"`) thay vì xin xác nhận (`yes_no`). Mục "Sending and posting" trong `system_prompt.md` đã được viết lại sau khi chạy v2. Giữ nguyên `tools.yaml`, chỉ chạy lại:

```bash
python run_eval.py --provider gemini --version v3 --suite base --eval-cases data/eval_base.json
```

Ghi dòng v3 vào `artifacts/version_log.csv`:

- `changed_artifact`: `artifacts/system_prompt.md`
- `metric_before`: `0.95`
- `hypothesis`: *Một yêu cầu gửi chưa phải là xác nhận; bắt buộc clarify yes_no trước sẽ sửa R12*
- hash và tên file run: lấy từ output của eval

Nên chạy v3 **hai lần**. R12 đã PASS ở v1 rồi FAIL ở v2 dù prompt không đổi (cùng hash `a606...`), tức là case này **không ổn định**. Hai lần chạy cho bằng chứng về độ ổn định, đưa vào B6.

## Bước 2: v4, viết lại `tools.yaml` và khai báo 4 tool mới

```bash
cp artifacts/tools_v4.yaml artifacts/tools.yaml
cp data/eval_group.next.json data/eval_group.json
pytest -q                     # phải xanh: khoảng 116 passed
python run_eval.py --provider gemini --version v4 --suite base  --eval-cases data/eval_base.json
python run_eval.py --provider gemini --version v4 --suite group --eval-cases data/eval_group.json
```

Ghi dòng v4 vào `version_log.csv`:

- `changed_artifact`: `artifacts/tools.yaml`
- `metric_before`: điểm v3
- `metric_after`: điểm base, ghi thêm điểm group trong cột `reason`
- `hypothesis`: *Description có làm gì / khi nào dùng / khi nào không dùng / quy ước args sẽ giữ base và giúp route đúng 4 tool mới*

Tuỳ chọn, chạy thêm eval extension để có thêm số liệu:

```bash
python run_eval.py --provider gemini --version v4 --suite extension --eval-cases data/eval_research_extension.json
```

Nếu eval group có case FAIL, đó là nguyên liệu cho **v5**. Ví dụ: thêm vào prompt một bảng routing cho 4 tool mới. Mỗi lần vẫn chỉ đổi một thứ.

## Bước 3: UI và link dùng thử (trước 16:30)

Terminal 1:

```bash
streamlit run app.py
```

Terminal 2:

```bash
brew install cloudflared      # nếu chưa có
cloudflared tunnel --url http://localhost:8501
```

Copy URL `https://....trycloudflare.com` vào `REPORT.md` → A1 → "URL:". Giữ cả hai Terminal mở suốt buổi showdown.

UI chạy cùng vòng lặp tool với `chat.py` và tự lưu transcript vào `transcripts/*ui*.transcript.json`.

## Bước 4: chat live, ít nhất 3 lượt, có transcript

Có thể chat trên UI hoặc chạy `python chat.py --provider gemini --version v4`. Nên thử 4 kịch bản:

1. `Tin tức AI hôm nay có gì nổi bật?` (research bình thường; cần `TAVILY_API_KEY` để có kết quả thật)
2. `Tóm tắt bài này giúp mình` → agent hỏi lại → `https://openai.com/research/` (cần `FIRECRAWL_API_KEY`)
3. `Đăng bản tin AI hôm nay lên Telegram` → agent phải hỏi xác nhận, chưa được gửi
4. `Trên Hacker News gần đây mọi người bàn gì về AI agents?` (tool mới, không cần key)

Đưa tên file transcript và tóm tắt từng lượt vào REPORT B4.

## Bước 5: hoàn thiện REPORT Phần B

| Mục | Lấy số liệu từ |
|---|---|
| B1 | các dòng v3, v4 trong `version_log.csv` |
| B2 | thêm các case FAIL của v2 (R12) và v3/v4 nếu có |
| B3 | 10 case nhóm và kết quả PASS/FAIL của run `v4_B_group_...json` |
| B4 | transcript ở Bước 4 |
| B5 | đã điền sẵn phần unit test và UI; thêm `send` nếu làm Telegram |
| B6 | Reflection: thay đổi nào tăng điểm nhiều nhất (v1, +30 điểm), case nào không ổn định (R12), unit test bắt được gì mà eval không bắt được |

## Bước 6: nộp bài

```bash
python scripts/parse_runs.py runs/ --output analysis/all_runs.csv
pytest -q
git status            # KHÔNG được thấy .env trong danh sách
```

Checklist:

- [ ] `version_log.csv` có v0–v4
- [ ] `runs/*.json`
- [ ] `transcripts/*.json`
- [ ] `eval_group.json` có 10 case
- [ ] `pytest` xanh
- [ ] REPORT có Phần A và Phần B
- [ ] Không có key trong bất kỳ file nào
