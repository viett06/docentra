# Docentra MVP — Bài toán, giải pháp và phạm vi

Nguồn yêu cầu là chat [docentra](https://chatgpt.com/c/6ae2ccc6-c7a4-83ec-82ac-8fb6e9337700). Mục tiêu là bản chạy xuyên suốt trong 21 ngày và có bằng chứng để quyết định chuẩn bị pilot.

## Pain point → hành vi sản phẩm

| Pain point HR | Giải pháp đã triển khai | Cách kiểm chứng |
| --- | --- | --- |
| Phải mang tập giấy đến máy scan, tháo/lật và scan theo nhu cầu | Web responsive, chọn employee trước, camera stream hoặc upload ảnh, nhiều trang/nhóm giấy tờ | Thử thiết bị và đo capture active time; việc lật/chụp vẫn cần con người |
| Sau scan phải tải xuống, tách file, đặt tên và phân loại thủ công | Nhóm trang thủ công trước gửi; ảnh đi thẳng vào private object storage; OCR và classification tạo document/field tự động | Demo một phiên nhiều nhóm, kiểm nguồn và thứ tự; tự splitting cả tập là P1 |
| Thiếu metadata và khó tìm thông tin chi tiết | Danh mục 3 loại, dữ liệu có cấu trúc đã duyệt, bộ lọc và full-text OCR | Tìm theo mã/người/loại/giá trị/nội dung, mở scan từ kết quả |
| AI có thể đọc sai hoặc gắn nhầm người | Bản review cạnh ảnh nguồn, giữ prediction gốc, version conflict, xác nhận đúng chủ thể, chặn OCR mã nhân viên mâu thuẫn | Test stale version, sai mã và sửa ngày; không auto-verify theo confidence |
| Hồ sơ mật có thể lộ qua URL hoặc quyền quá rộng | Auth cookie có phiên DB/thu hồi, CSRF, grant theo employee, role, bucket private, stream ảnh qua kiểm quyền | Tài khoản chụp/outsider/admin không mặc định đọc hoặc duyệt nội dung |
| Số hóa chưa đủ khiến HR hiểu nhầm giấy tờ bị thiếu | Tra cứu chỉ bản đã verified; endpoint coverage phân biệt chưa số hóa/chưa duyệt/bị từ chối | Không trả “không tồn tại trên giấy” chỉ vì không có kết quả số hóa |
| Khó chứng minh hiệu quả | Lưu output AI/version riêng, audit và review history, generator và evaluator synthetic, mẫu nghiên cứu thời gian A/B | Báo n/N trước review; HR time study riêng, không suy thời gian thao tác từ khoảng cách log |

## Những gì có trong bản local

Pydantic schema cho login, scan session, manifest, phân nhóm, field updates và verification; SQLAlchemy chỉ định nghĩa cấu trúc bảng. Alembic có 15 bảng gồm phiên đăng nhập và trigger bảo vệ ảnh gốc/lịch sử/nội dung verified. Các condition nghiệp vụ nhiều bảng được thực thi trong services và transaction.

Upload có giới hạn bytes/dimensions, kiểm định dạng bằng decode, checksum SHA-256, mã chống trùng và manifest đủ trang. S3 và DB không có transaction chung: object có thể thành orphan nếu DB commit lỗi; ảnh đã có record được giữ nguyên, không âm thầm ghi đè. Chưa có tác vụ purge orphan tự động hoặc xóa dữ liệu production.

Worker polling PostgreSQL: claim `SKIP LOCKED`, lease token, heartbeat, backoff, tối đa 3 attempt; output publish atomically. Worker hết lease không được commit kết quả. Job/output giữ nguyên khi HR sửa trường. Tesseract là baseline thực sự; confidence từ OCR không phải xác suất đã hiệu chuẩn.

HR phải đối chiếu mọi trường. Trường present cần nguồn thuộc tài liệu, ngày cần parse hợp lệ, trường required cần giá trị, job/manifest/OCR phải đầy đủ, và đúng employee. Unknown/chọn sai người không tự được công bố. Muốn sửa verified phải reopen có lý do; tài liệu rời kho tra cứu trong thời gian sửa.

Search normal chỉ verified và đúng scope. Full-text OCR có thể tìm qua chữ nhận dạng sai, vì vậy kết quả vẫn phải mở nguồn. CSV xuất trường đã xác minh và source ID, có chặn công thức spreadsheet trong giá trị xuất.

## Lựa chọn công nghệ cho MVP

- React/Vite theo frontend P-029 thay vì thêm Next.js; FastAPI serve bundle cùng origin giúp auth cookie và source viewer gọn hơn cho local demo.
- Tesseract Việt/Anh thay baseline PaddleOCR đề xuất ban đầu: cài được trong image CPU, không cần nhà cung cấp ngoài; có benchmark và có thể thay engine sau khi so sánh trên tập đã đóng băng. Cách lấy text/confidence theo [Tesseract TSV](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html).
- PostgreSQL làm hàng đợi durable thay Redis ở quy mô demo: không có khoảng hở commit-DB/publish-Redis; retry và lease có kiểm thử. Nếu mở rộng, có thể thêm Redis đánh thức worker mà vẫn giữ DB là nguồn trạng thái.
- MinIO private, không public object URL. Dữ liệu demo lưu local; không đăng site hoặc đẩy dữ liệu lên cloud.

## Giới hạn cần giữ rõ

Chưa có tự động chia cả tập hồ sơ, chỉnh ranh giới sau xử lý trên UI, semantic search/RAG, SAP sync, PDF import, antivirus, SSO, reset password, device management hoặc công cụ cấu hình quyền trong giao diện. Quyền/tài khoản demo được seed bằng script. API coverage đã có, UI kho hiện tập trung vào tài liệu và thông báo trạng thái trống.

Không có HR time study hoặc kiểm thử camera trên thiết bị bệnh viện tự động. Không tuyên bố đạt chứng nhận bảo mật, chất lượng trên hồ sơ thật hoặc tiết kiệm X% thời gian. Pilot chỉ bắt đầu sau khi dữ liệu, thiết bị, nơi lưu, quyền, retention/backup và trách nhiệm vận hành được đơn vị có thẩm quyền phê duyệt.
