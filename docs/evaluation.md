# Đánh giá MVP

Ba nhóm bằng chứng tách biệt: correctness của phần mềm, chất lượng OCR/rules trước review, và thời gian/khả dụng với HR. Test dùng OCR mock chỉ chứng minh workflow, không là kết quả AI.

## Kiểm thử phần mềm

```bash
venv/bin/python -m pip install -r requirements-dev.txt
DOCENTRA_RUN_DB_TESTS=1 venv/bin/python -m pytest -q
venv/bin/ruff check app alembic scripts tests
npm run build --prefix frontend
```

Integration chạy PostgreSQL thật trong database tạm riêng và storage/OCR có kiểm soát. Kiểm auth/logout/CSRF/Origin, dữ liệu ảnh thực thay MIME filename, retry không trùng, manifest thiếu/sai, job idempotency, toàn luồng duyệt/search/CSV, sai người, stale version, unknown, quyền outsider/capture/admin và DB trigger. Lease test kiểm worker cũ mất quyền heartbeat sau khi lease bị thu hồi.

## Dataset synthetic có version

```bash
mkdir -p .data
docker compose run --rm --no-deps --user "$(id -u):$(id -g)" -v "$PWD/.data:/work" api \
  python -m app.demo.generate --output /work/benchmark-v1 --employees 30
```

Generator tạo 30 chủ thể, 90 tài liệu thuộc 3 loại + 10 unknown, tổng 220 trang. Ground truth gồm loại, field/value và trang nguồn; manifest có hash ảnh, split và layout family. Dữ liệu nằm ngoài Git. Tạo thư mục version mới thay vì ghi đè manifest đã có.

Chia dev/validation/test theo employee để không trùng chủ thể. Có thay đổi margin/layout và ảnh mờ/xoay nhẹ, nhưng vẫn là biểu mẫu do cùng renderer sinh ra. Các family không đại diện cho mẫu giấy tờ thật độc lập; không gọi đây là bằng chứng tổng quát hóa trên biểu mẫu bệnh viện. Ảnh chụp bản in trên thiết bị thật là tập đánh giá tiếp theo.

## Đo OCR trước HR sửa

```bash
docker compose run --rm --no-deps --user "$(id -u):$(id -g)" -v "$PWD/.data:/work" api \
  python -m app.demo.evaluate --manifest /work/benchmark-v1/manifest.jsonl \
  --split dev --limit 10 --output /work/evaluation/dev-smoke.json
```

Evaluator chỉ đưa bytes ảnh vào pipeline; ground truth chỉ dùng để chấm sau khi có output. Worker vận hành không đọc module fixtures/generate hay ground truth. Báo cáo giữ manifest hash và pipeline source hash, n/N theo từng metric, kết quả từng field, phân loại từng lớp, unknown rejection, nguồn trên giá trị đã trích đúng, latency p50/p95 của pipeline offline.

Phép đo `--limit 10 --split dev` là smoke test trên mẫu nhỏ, không là held-out test hay kết quả cam kết. Sau khi chốt rule/config, đóng băng version và chạy validation/test riêng; không sửa thuật toán trên test rồi trình số đó như một test mới. Latency offline không gồm upload/queue/HR; cần đo vận hành riêng.

Các ngưỡng trong PRD (ví dụ phân loại/trích xuất ≥90%) vẫn là mục tiêu cần HR/mentor xác nhận, không phải kết quả mặc định. Không dùng confidence OCR như tỷ lệ chính xác đã được hiệu chuẩn.

## Đo giá trị với HR

Mẫu ghi tại [evaluation/time-study.template.csv](../evaluation/time-study.template.csv). Mỗi cặp tác vụ có hai hồ sơ giả cùng loại/số trang/độ khó, đảo thứ tự A/B và có vòng tập trước khi đo. A là quy trình thủ công tương đương; B là Docentra, cùng chất lượng đầu ra.

Ghi riêng capture active, review active, organize active, retrieve active, upload wait, AI wait và wall-clock; số trang/lần chụp lại/trường sửa. Không lấy khoảng giữa audit timestamps làm thời gian thao tác chủ động. Không cộng thời gian đi kho/tháo ghim nếu chưa đo vật lý.

```bash
python3 scripts/summarize_time_study.py evaluation/time-study.completed.csv
```

Script báo trung vị tiết kiệm từng cặp cho tổng thời gian chủ động và phần sau scan; không loại ca chậm hoặc lỗi. Đây chỉ là phép tổng hợp, không thay validation với người dùng thật. Chưa có buổi HR hoặc kết quả điền tay trong repository.

## Điều kiện chuyển tiếp

P0 phải chạy xuyên suốt, không có lỗi chặn sai người/mất trang/quyền, có số đo AI trước review, HR thực hiện được tác vụ và xác nhận giá trị. Nếu thiếu bằng chứng, ghi rõ chưa đo và người chịu trách nhiệm bổ sung. Qua MVP là quyết định chuẩn bị pilot; dữ liệu thật vẫn cần phê duyệt riêng.
