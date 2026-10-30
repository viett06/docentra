# Kiểm chứng bản local ngày 30/10/2026

## Phần mềm và hạ tầng

- 25 ca pytest đạt: unit parsing/schema/image, TLS/CA/địa chỉ Wi-Fi và integration với PostgreSQL tạm riêng; không ghi dữ liệu kiểm thử vào database demo.
- TypeScript/Vite build đạt; Ruff đạt; npm báo không có vulnerability đã biết tại lần kiểm tra này.
- Alembic head `0004`: 15 bảng nghiệp vụ + bảng version; `alembic check` không phát hiện schema drift.
- Docker API, PostgreSQL và MinIO healthy; worker chạy và xử lý job OCR thật.
- Đọc ẩn danh một ảnh scan thật trong bucket bị MinIO từ chối HTTP 403.
- Trình duyệt: đăng nhập reviewer → thêm hợp đồng synthetic 2 trang → upload → job thành công → mở bản scan → đối chiếu cả 4 trường → xác nhận employee → verified. Có kiểm tra viewport 375 px không tràn ngang.

Integration sử dụng OCR/storage mock để chủ động kiểm tra trường hợp lỗi. Phần OCR dưới đây và browser demo dùng Tesseract thật trong Docker.

HTTP smoke test bổ sung đã gửi một phiên chứa 4 nhóm qua storage/worker thật: hợp đồng, bằng cấp, chứng chỉ có giá trị khớp ground truth synthetic và được xác minh; mẫu unknown giữ `NEEDS_REVIEW`. Script kiểm thử không thay thế HR; chỉ tự xác nhận khi dữ liệu giả khớp toàn bộ giá trị kỳ vọng.

## OCR smoke test trước HR review

Bộ dữ liệu đã tạo tại `.data/benchmark-v1`: 30 nhân viên giả, 100 tài liệu, 220 trang; split dev 60 / validation 20 / test 20 tài liệu theo employee.

Đã chạy **10 tài liệu đầu của tập dev**, gồm 9 known và 1 unknown, không chạy held-out test để trình thành kết quả tổng quát:

| Chỉ số | Kết quả thô |
| --- | --- |
| Phân loại known | 9/9 |
| Unknown được từ chối | 1/1 |
| Giá trị trường exact match | 36/36 |
| Nguồn đúng trên giá trị đã trích đúng | 36/36 |
| Pipeline offline p50 / p95 mỗi tài liệu | 1,040 / 1,523 giây |

Kết quả từng trường, manifest hash và pipeline source hash ở `.data/evaluation/dev-smoke.json`. Đây là mẫu rendered nhỏ, sạch, theo các nhãn chuẩn đã cấu hình; chưa đại diện ảnh chụp kho hoặc biểu mẫu thực. Không dùng các tỷ lệ trên như chất lượng được cam kết. Thời gian offline không gồm upload, queue hoặc HR.

## Chưa có bằng chứng

Chưa có time study với HR, ảnh chụp trên điện thoại thực tế của bệnh viện, dữ liệu thật được phê duyệt, restore/retention drill hoặc đánh giá bảo mật production. Có template và script cho bước đo HR, nhưng chưa điền kết quả giả để thay người dùng thực hiện.

## Webapp scan Android qua HTTPS nội bộ

- Frontend build TypeScript/Vite đạt. Viewport 375 px có `scrollWidth == innerWidth == 375`; đã kiểm tra đăng nhập vai trò CAPTURE từ `?scan=1`, preview ảnh lớn, đổi thứ tự bằng so sánh URL ảnh trước/sau và gửi hợp đồng giả lập hai trang tới worker thật. Giao diện báo OCR hoàn tất, chờ HR.
- HTTPS dùng CA riêng và kiểm tra IP SAN, không tắt certificate verification. Đã kiểm tra login/me/logout với CSRF, cookie Secure/SameSite=Strict, quyền đọc 30 hồ sơ được cấp và từ chối CAPTURE truy cập search.
- HTTP smoke qua HTTPS Wi-Fi thật với CA đã xác thực: hợp đồng hai trang, bằng cấp, chứng chỉ và unknown. Ba loại known có trường khớp ground truth synthetic; cả bốn giữ NEEDS_REVIEW. Không tự xác minh thay HR trong lần đo này.
- Bảy ca mới kiểm tra TLS không chấp nhận CA sai/IP sai, bootstrap chỉ trả hướng dẫn/QR/CA công khai, không trả khóa riêng/API, giữ CA khi đổi IP và từ chối địa chỉ public hoặc chuỗi không phải IPv4.
- Android thật đã được người dùng xác nhận quét QR và mở được trang kết nối sau khi chuyển máy tính sang hotspot của điện thoại. Với Wi-Fi trước đó, server hoạt động trên máy tính, firewall macOS không bật, route đi qua Wi-Fi nhưng chưa thấy phản hồi ARP từ điện thoại. Chưa xác định chính sách mạng cụ thể gây lỗi ở Wi-Fi cũ. Việc cài CA, mở webapp HTTPS và chụp bằng camera Android vẫn cần xác nhận trên thiết bị.

Lặp lại kiểm tra transport bằng `venv/bin/python -m scripts.smoke_api --url https://<IP-Wi-Fi>:8443 --ca-file .data/mobile/public/docentra-ca.crt --employee-code SYN-EMP-004`. Đây vẫn là kiểm tra HTTP và synthetic OCR, không phải thử nghiệm camera vật lý. Hướng dẫn kết nối nằm trong [mobile.md](mobile.md).
