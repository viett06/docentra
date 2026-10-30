# Docentra

Docentra hỗ trợ số hóa, xác minh và tra cứu hồ sơ nhân sự. Các thuật ngữ bên dưới dùng thống nhất trong MVP.

## Language

**Employee — Nhân viên**:
Người có hồ sơ cần số hóa; không nhất thiết là người đăng nhập Docentra.
_Avoid_: User khi nói về chủ thể hồ sơ.

**Scan session — Phiên scan**:
Một lượt chụp và gửi các trang của đúng một nhân viên. Một phiên có thể chứa nhiều tài liệu.
_Avoid_: Tài liệu khi nói về cả lượt chụp.

**Scan page — Trang scan**:
Một mặt giấy được chụp trong phiên scan; bản chụp lại là một trang mới thay thế trang đã loại.
_Avoid_: Tờ giấy khi chỉ có ảnh một mặt.

**Document — Tài liệu**:
Một giấy tờ nghiệp vụ hoàn chỉnh như hợp đồng, bằng cấp hoặc chứng chỉ; có thể gồm nhiều trang scan.
_Avoid_: Hồ sơ khi nói về một giấy tờ.

**Employee dossier — Hồ sơ nhân viên**:
Tập các tài liệu thuộc về một nhân viên, có thể được số hóa qua nhiều phiên scan.
_Avoid_: Scan session khi nói về toàn bộ hồ sơ.

**Field prediction — Đề xuất trường dữ liệu**:
Giá trị AI đọc được hoặc nhận định không đọc được từ tài liệu, trước khi người kiểm duyệt sửa.
_Avoid_: Thông tin đã xác minh.

**Verified document — Tài liệu đã xác minh**:
Tài liệu đã được người có quyền kiểm tra chủ thể hồ sơ, loại giấy tờ, nội dung và trang nguồn.
_Avoid_: Tài liệu hợp pháp; xác minh ở đây không phải chứng nhận pháp lý.

**Source page — Trang nguồn**:
Trang scan làm bằng chứng cho một trường dữ liệu hoặc một kết quả tra cứu.
_Avoid_: Link ảnh khi nói về bằng chứng nghiệp vụ.
