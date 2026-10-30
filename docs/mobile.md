# Scan bằng Android / Chrome trong cùng Wi-Fi

Máy tính chạy PostgreSQL, MinIO, worker và FastAPI. Điện thoại dùng webapp responsive qua HTTPS; không cần cài APK. Ảnh camera trực tiếp được mã hóa JPEG trong trình duyệt, kiểm tra trước khi nhận, sau đó gửi qua API và pipeline OCR hiện có.

## Mở dịch vụ

Từ thư mục gốc dự án:

```bash
docker compose up -d api worker
venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix frontend run build
venv/bin/python -m scripts.mobile
```

Script tự tìm IPv4 Wi-Fi trên macOS, tạo CA riêng của project và chứng chỉ server 90 ngày, sau đó in hai địa chỉ:

- `http://<IP-Wi-Fi>:8081/`: hướng dẫn Android, QR và tải **chứng chỉ CA công khai**. Trang này không có đăng nhập, ảnh hay API nghiệp vụ.
- `https://<IP-Wi-Fi>:8443/?scan=1`: toàn bộ webapp/FastAPI với cookie `Secure`. Đăng nhập xong vào ngay màn hình số hóa cho vai trò CAPTURE/REVIEWER.

Giữ terminal chạy. `Ctrl+C` dừng cả hai listener và tiến trình HTTPS con. API Docker `127.0.0.1:8080` vẫn hoạt động cho desktop, cùng database và worker. HTTPS host dùng file `.env` và frontend đã build; sau khi sửa frontend cần build lại, sửa Python cần khởi động lại script.

Nếu tự nhận IP sai do VPN hoặc nhiều card mạng:

```bash
venv/bin/python -m scripts.mobile --host 192.168.1.12
```

Thay IP bằng địa chỉ Wi-Fi thực của máy. Chỉ bind IP nội bộ đã chọn, không dùng public tunnel. Khi Wi-Fi đổi IP, dừng rồi chạy lại script: chứng chỉ server/QR đổi theo IP, CA cũ được giữ nên điện thoại không cần cài lại CA. CA/key/QR/log nằm trong `.data/mobile`, đã gitignore; không gửi khóa `.key` cho điện thoại.

## Cấu hình Android một lần

1. Máy tính và điện thoại dùng cùng Wi-Fi. Mở URL HTTP `:8081` trên máy tính để hiện QR; quét QR bằng điện thoại.
2. Tải `docentra-ca.crt`. Đối chiếu SHA-256 với fingerprint script in trên máy tính.
3. Mở **Cài đặt → Bảo mật và quyền riêng tư → Cài đặt bảo mật khác → Mã hóa và thông tin xác thực → Cài đặt chứng chỉ → Chứng chỉ CA**, chọn file vừa tải. Tên menu tùy hãng; có thể tìm “Chứng chỉ CA” trong Cài đặt. Đây là chứng chỉ CA, không phải chứng chỉ Wi-Fi/client. [Hướng dẫn Android của Google](https://support.google.com/pixelphone/answer/2844832?hl=vi).
4. Mở lại Chrome nếu cần rồi nhấn **Mở Docentra HTTPS** trên trang hướng dẫn. Nếu chứng chỉ vẫn không hợp lệ, kiểm tra đúng CA, IP và thời gian thiết bị; hoàn tất tin cậy trước khi đăng nhập.
5. Đăng nhập `capture@docentra.local`, mật khẩu demo `DocentraDemo!2026` nếu chưa đổi. Chọn đúng nhân viên, **Mở camera**, cho phép Camera. Không cần quyền micro.

`getUserMedia()` cần secure context và quyền camera; dùng IP LAN qua HTTP không đáp ứng điều kiện này. [Tài liệu MediaDevices](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

## Một phiên scan

1. Chọn đúng nhân viên; mỗi giấy tờ nằm trong một nhóm.
2. Camera ưu tiên camera sau. Căn giấy theo khung, chụp rồi xem ảnh: rõ chữ, đủ góc, không lóa.
3. **Nhận & chụp tiếp** để lật và chụp liên tiếp; **Nhận & xong** quay về danh sách. Khung không tự crop hoặc chỉnh phối cảnh; toàn bộ khung ảnh được giữ.
4. Chạm thumbnail để xem lớn; **Chụp lại trang này** chỉ thay ảnh sau khi nhận ảnh mới, giữ nguyên vị trí. Hủy camera giữ nguyên ảnh cũ. Có nút chuyển thứ tự và bỏ trang.
5. **Thêm giấy tờ khác** để tạo nhóm mới. Thanh gửi cố định cuối màn hình hiển thị tổng trang; tối đa 30 trang/phiên, 10 MB và 24 megapixel/ảnh.
6. **Gửi & xử lý**: giữ tab mở, xem tiến độ. Retry gửi lại giữ ID phiên/trang để không tạo bản trùng. HR mở desktop, đối chiếu từng trường với scan, xác minh rồi tìm trong kho.

Chuyển ứng dụng/tab sẽ dừng camera; mở lại camera khi quay về. Ảnh đã nhận và ảnh vừa chụp đang xem được giữ khi tab còn sống. Nếu Android hủy tab, mất nguồn hoặc reload trước khi gửi thì ảnh chờ có thể mất; không có lưu offline. Chế độ **Dùng camera của máy** là phương án dự phòng qua file picker và có thể ghi ảnh vào thư viện tùy Android; chế độ camera trực tiếp không chủ động lưu ảnh vào thư viện.

## Khi chưa kết nối được

- Không mở được `:8081`: kiểm tra cùng Wi-Fi, đúng IP, terminal còn chạy, macOS firewall cho phép Python nhận kết nối mạng nội bộ. Wi-Fi khách có thể chặn thiết bị nhìn thấy nhau. Chưa cần đổi cổng database hoặc MinIO.
- HTTPS mở được nhưng camera bị từ chối: mở quyền trang web trong Chrome, cho phép Camera; kiểm tra quyền Camera của ứng dụng Chrome trong Cài đặt Android. Đóng ứng dụng khác đang dùng camera.
- Ảnh quá lớn/không hỗ trợ: chọn JPEG/PNG/WebP hoặc giảm độ phân giải camera máy. Camera trực tiếp tạo JPEG.
- Job chờ mãi: kiểm tra `docker compose ps` và worker. Ảnh đã upload nằm trong storage; retry không yêu cầu tạo phiên khác.

Chỉ dùng hồ sơ giả lập cho bản demo. Kiểm thử tự động xác minh TLS/CA, giới hạn truy cập file bootstrap và nghiệp vụ; chưa thay thế thử nghiệm camera, mạng Wi-Fi và quyền thiết bị trên điện thoại thực tế. Sau thử nghiệm có thể gỡ “Docentra Local Demo CA” khỏi chứng chỉ người dùng của Android. CA chỉ cấp cho IP mạng nội bộ/localhost theo name constraints, và khóa riêng chỉ ở máy tính.
