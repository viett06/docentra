# Docentra

MVP số hóa hồ sơ nhân sự: **chụp/gửi ảnh → OCR, phân loại và trích xuất → HR đối chiếu → xác minh → tra cứu đúng trang nguồn**.

Ứng dụng chạy local bằng Docker và chỉ dùng dữ liệu giả lập. Không thay thế SAP hoặc tự xác nhận giá trị pháp lý của giấy tờ.

## Chạy sản phẩm

Từ thư mục gốc, với Docker Desktop đang chạy:

```bash
python3 scripts/init_env.py
docker compose up --build -d --wait api worker
```

Mở **[Docentra](http://127.0.0.1:8080)**. OpenAPI tại **[API docs](http://127.0.0.1:8080/docs)**. Compose tự áp dụng migration, tạo bucket private và seed tài khoản/30 nhân viên giả trước khi API và worker khởi động.

| Tài khoản demo | Chức năng |
| --- | --- |
| `reviewer@docentra.local` | Chụp, đối chiếu, sửa, duyệt, tra cứu hồ sơ được giao |
| `capture@docentra.local` | Chụp/gửi và theo dõi phiên của mình; không duyệt hoặc tra kho |
| `viewer@docentra.local` | Chỉ tra cứu và xuất dữ liệu đã xác minh |
| `admin@docentra.local` | Xem audit vận hành; không mặc định đọc nội dung hồ sơ |
| `outsider@docentra.local` | Không có hồ sơ được cấp quyền; dùng kiểm tra cách ly |

Mật khẩu demo mặc định từ `scripts/init_env.py`: **`DocentraDemo!2026`**. Nếu `.env` đã có `DEMO_PASSWORD`, giá trị đó được giữ nguyên. Seed không đổi mật khẩu tài khoản đã tồn tại. Các tài khoản này chỉ phục vụ môi trường synthetic được bind vào loopback.

PostgreSQL: `127.0.0.1:5433`, database/user `docentra`; mật khẩu trong `.env`. MinIO API `127.0.0.1:9002`, console `127.0.0.1:9003`; thông tin đăng nhập là `S3_ACCESS_KEY/S3_SECRET_KEY` trong `.env`. Bucket không public; ứng dụng kiểm quyền và stream ảnh qua backend.

`migrate` và `seed` kết thúc với exit code 0 là bình thường. `api`, `worker`, `db`, `minio` tiếp tục chạy. Dừng dịch vụ bằng `docker compose stop`; dữ liệu nằm trong hai volume của project Docentra.

## Demo 5–7 phút

1. Đăng nhập HR reviewer, mở **Số hóa hồ sơ**, chọn `SYN-EMP-001`.
2. Dùng camera hoặc **Thêm tài liệu mẫu** để nhận ảnh giả lập. Hợp đồng mẫu có hai trang. Tách mỗi giấy tờ vào một nhóm, đổi thứ tự/bỏ trang/chụp lại trước khi gửi.
3. Chọn **Gửi & xử lý**. Mỗi ảnh có receipt; job chạy OCR thật trong worker, không lấy đáp án từ dữ liệu seed.
4. Vào **Kiểm tra & xác minh**, mở tài liệu, đọc ảnh gốc, sửa trường nếu cần, chọn trang nguồn và đánh dấu đã đối chiếu từng trường.
5. Xác nhận đúng nhân viên rồi xác minh. Vào **Kho tài liệu**, tìm theo mã/giá trị/nội dung OCR, mở đúng scan hoặc xuất CSV.
6. Thử mẫu **Chưa xác định** hoặc tài khoản outsider để thấy tài liệu không tự được duyệt và dữ liệu không lộ ngoài phạm vi. Mở lại tài liệu đã duyệt sẽ gỡ nó khỏi kho tra cứu đến lần xác minh sau.

Camera dùng `getUserMedia` và giữ ảnh chờ trong bộ nhớ tab; ứng dụng không ghi localStorage, IndexedDB hoặc cache offline. Không đóng tab khi còn ảnh chưa gửi. Camera trên điện thoại cần môi trường HTTPS tin cậy và đường kết nối được phép tới backend; cấu hình mặc định chỉ mở trên máy local. Chưa có xác nhận không còn dữ liệu tạm ở cấp OS/browser hoặc thử nghiệm thiết bị bệnh viện.

### Scan trên Android / Chrome, cùng Wi-Fi

Sau khi build frontend bằng `npm --prefix frontend run build`, chạy **`venv/bin/python -m scripts.mobile`**. Script mở HTTPS nội bộ và trang hướng dẫn/QR; giữ nguyên API Docker cho desktop. Điện thoại cài CA do project tạo một lần, rồi dùng camera sau để chụp → xem lại → nhận/chụp tiếp. Có preview lớn, chụp lại từng trang giữ vị trí và thanh gửi dành cho mobile. [Hướng dẫn Android và xử lý lỗi](docs/mobile.md).

## Cấu trúc

```text
main.py          # Khởi tạo FastAPI, router, middleware, xử lý lỗi, health/readiness và web
app/model/       # SQLAlchemy: chỉ định nghĩa bảng, theo quy ước P-029
app/schema/      # Pydantic: request/response và validation
app/api/         # FastAPI controllers
app/services/    # nghiệp vụ, quyền, storage, pipeline
app/db/          # Base, cấu hình và session
app/worker.py    # queue PostgreSQL + retry/lease
app/demo/        # renderer/generator/evaluator synthetic; worker không đọc ground truth
frontend/        # React + TypeScript + Vite
alembic/         # migration schema, catalog và trigger bảo vệ lịch sử
tests/           # unit + integration trên DB tạm riêng
docs/            # kiến trúc, API, scope MVP và đánh giá
```

FastAPI/SQLAlchemy giữ cấu trúc gần P-029. Frontend dùng React/Vite cùng cách triển khai frontend P-029 và được FastAPI serve cùng origin. Queue dùng PostgreSQL bền vững với `FOR UPDATE SKIP LOCKED`, retry và lease fencing, chưa cần Redis cho quy mô MVP. OCR baseline self-hosted là Tesseract `vie+eng`, rồi rules/regex; không gọi dịch vụ AI bên ngoài. [Thiết kế và giới hạn](docs/mvp.md).

## Phát triển và migration

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements-dev.txt
venv/bin/alembic upgrade head
venv/bin/alembic check
venv/bin/ruff check app alembic scripts tests
venv/bin/python -m pytest -q
DOCENTRA_RUN_DB_TESTS=1 venv/bin/python -m pytest -q
```

Integration tests tạo/xóa các database `docentra_test_*` trên PostgreSQL local, dùng image storage/OCR giả lập có kiểm soát để kiểm chứng nghiệp vụ. Chúng không xóa dữ liệu demo. Thử OCR thật là phép đo riêng, không được gọi test với OCR mock là chứng minh độ chính xác AI.

Sau khi đổi ORM: `venv/bin/alembic revision --autogenerate -m "describe_change"`, đọc migration rồi `upgrade head`. Không dùng `create_all()` thay migration. Chi tiết trong [database.md](docs/database.md).

Để sửa UI/backend trên host, dừng container API tránh chiếm cổng; giữ DB/MinIO/worker nếu cần:

```bash
docker compose stop api
venv/bin/python main.py
# Terminal khác:
cd frontend
npm ci
npm run dev
```

Frontend dev proxy `/api` về `127.0.0.1:8080`. Worker phải được rebuild khi sửa pipeline. Không bật autogenerate migration lúc API khởi chạy.

`main.py` là entrypoint FastAPI duy nhất. `python main.py` chạy Uvicorn ở `127.0.0.1:8080` với auto-reload để phát triển; cũng có thể dùng `uvicorn main:app --host 127.0.0.1 --port 8080 --reload --no-access-log`. Docker tiếp tục dùng `main:app` trên cổng nội bộ 8000, không bật reload.

## Dữ liệu và đánh giá

Hướng dẫn tạo **30 hồ sơ giả, 100 tài liệu, 220 trang**, chia theo nhân viên, chạy OCR benchmark trước review và đo thời gian HR nằm trong [evaluation.md](docs/evaluation.md). Kết quả synthetic không chứng minh chất lượng trên hồ sơ thật. Nhận dữ liệu thật/pilot cần bước phê duyệt riêng như PRD.

Smoke test xuyên suốt HTTP/storage/worker thật: `venv/bin/python -m scripts.smoke_api`. Thêm `--verify` chỉ dùng cho local synthetic để xác minh các tài liệu có mọi giá trị khớp ground truth renderer; unknown vẫn chờ HR. Script tạo phiên demo mới, không xóa phiên cũ. [Kết quả kiểm chứng hiện tại](docs/verification.md).
