# API v1

OpenAPI tương tác: `http://127.0.0.1:8080/docs`.

| Nhóm | Endpoint | Nội dung |
| --- | --- | --- |
| Auth | `POST /api/v1/auth/login`, `GET /auth/me`, `POST /auth/logout` | Cookie HttpOnly, token CSRF, phiên có expiry/revoke |
| Catalog | `GET /employees`, `/document-types`, `/employees/{id}/coverage`, `/dashboard` | Dữ liệu thuộc phạm vi được cấp quyền |
| Capture | `POST /scan-sessions`, `GET /scan-sessions/{id}` | Client session UUID chống retry trùng |
| Ảnh | `POST /scan-sessions/{id}/pages` | Multipart file + client_page_id + page_order; trả receipt không có storage credential/key |
| Finalize | `POST /scan-sessions/{id}/finalize` | Version và manifest page ID/hash theo thứ tự |
| Process | `POST /scan-sessions/{id}/process` | Idempotency key và groups; mọi trang thuộc đúng một nhóm |
| Review | `GET/PATCH /documents/{id}`, `POST /documents/{id}/verify` | Giá trị, value_state, source và reviewed; verify cần identity_confirmed=true |
| Trạng thái | `POST /documents/{id}/reject`, `/reopen` | Version và reason; lưu history |
| Nguồn | `GET /pages/{id}/image` | Kiểm quyền và stream ảnh private với no-store |
| Retrieval | `GET /search?q=&type_code=&employee_id=&limit=&offset=` | Chỉ verified; scope, metadata, trường đã duyệt và OCR current job |
| Hàng đợi | `GET /review-queue` | Chỉ reviewer đúng phạm vi |
| Truy vết | `GET /documents/{id}/history`, `/audit` | History nhạy cảm chỉ reviewer; audit không chứa OCR/giá trị trường |
| Xuất | `GET /documents/{id}/export` | CSV chỉ tài liệu đã verified |
| Demo | `GET /demo/samples/{employee}/{type}/{page}?page_count=` | Chỉ DEMO_MODE và nhân viên SYN được cấp quyền capture |

Các đường dẫn rút gọn trong bảng đều có prefix `/api/v1`. `/health` và `/ready` nằm ngoài prefix.

Mọi request sau login dùng cookie; request thay đổi dữ liệu cần header `X-CSRF-Token` lấy từ login/me. Không lưu auth token trong localStorage. Request từ Origin khác bị từ chối. Đọc tài liệu/ảnh ngoài quyền trả 404 và ghi audit; capture không tự có quyền search/review; admin không tự có quyền nội dung.

PATCH và verify dùng `version`, stale version trả 409. Retry upload với cùng client page ID phải khớp bytes/hash/thứ tự; retry processing với cùng key phải khớp groups. Ngày chuẩn hóa ISO, value thiếu là null và có value_state rõ. Error response chỉ có code/message/request_id, không echo password, SQL params hoặc OCR payload.
