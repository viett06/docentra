"""Run the existing FastAPI app over trusted local HTTPS for Android capture."""

import argparse
import html
import ipaddress
import os
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, ProxyHandler, build_opener

import qrcode
import qrcode.image.svg

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8")
)


def lan_host(value: str) -> str:
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise argparse.ArgumentTypeError("Dùng địa chỉ IPv4 Wi-Fi, ví dụ 192.168.1.12") from exc
    if not any(address in network for network in PRIVATE_NETWORKS):
        raise argparse.ArgumentTypeError("Chỉ dùng IP mạng nội bộ hoặc loopback cho bản demo này")
    return str(address)


def detect_host() -> str:
    if sys.platform == "darwin":
        for interface in ("en0", "en1"):
            result = subprocess.run(["/usr/sbin/ipconfig", "getifaddr", interface], capture_output=True, text=True)
            if result.returncode == 0:
                return lan_host(result.stdout.strip())
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.connect(("192.0.2.1", 9))  # Choose a route; no application data is sent.
        return lan_host(connection.getsockname()[0])


def openssl(*args: str) -> str:
    binary = shutil.which("openssl")
    if not binary:
        raise RuntimeError("Cần OpenSSL để tạo chứng chỉ HTTPS nội bộ")
    result = subprocess.run([binary, *args], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("OpenSSL không tạo/kiểm tra được chứng chỉ. Kiểm tra quyền ghi .data/mobile.")
    return result.stdout.strip()


def prepare(directory: Path, host: str, port: int, setup_port: int) -> dict:
    host = lan_host(host)
    private, public = directory / "private", directory / "public"
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    private.chmod(0o700)
    public.mkdir(parents=True, exist_ok=True)
    ca_key, ca_cert = private / "ca.key", public / "docentra-ca.crt"
    if ca_key.exists() != ca_cert.exists():
        raise RuntimeError("Cặp chứng chỉ CA chưa đầy đủ. Khôi phục CA cũ hoặc đổi tên .data/mobile để tạo bộ mới.")
    if not ca_key.exists():
        openssl(
            "req",
            "-x509",
            "-newkey",
            "rsa:3072",
            "-nodes",
            "-sha256",
            "-days",
            "3650",
            "-subj",
            "/CN=Docentra Local Demo CA",
            "-keyout",
            str(ca_key),
            "-out",
            str(ca_cert),
            "-addext",
            "basicConstraints=critical,CA:TRUE,pathlen:0",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
            "-addext",
            "nameConstraints=critical,permitted;IP:10.0.0.0/255.0.0.0,permitted;IP:172.16.0.0/255.240.0.0,permitted;IP:192.168.0.0/255.255.0.0,permitted;IP:127.0.0.0/255.0.0.0,permitted;DNS:localhost",
        )
    ca_key.chmod(0o600)
    key, cert, csr = private / "server.key", private / "server.crt", private / "server.csr"
    extension = private / "server.ext"
    extension.write_text(
        f"basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=IP:{host},IP:127.0.0.1,DNS:localhost\n"
    )
    openssl(
        "req",
        "-new",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-sha256",
        "-subj",
        "/CN=Docentra Wi-Fi Demo",
        "-keyout",
        str(key),
        "-out",
        str(csr),
    )
    key.chmod(0o600)
    openssl(
        "x509",
        "-req",
        "-in",
        str(csr),
        "-CA",
        str(ca_cert),
        "-CAkey",
        str(ca_key),
        "-CAserial",
        str(private / "ca.srl"),
        "-CAcreateserial",
        "-out",
        str(cert),
        "-days",
        "90",
        "-sha256",
        "-extfile",
        str(extension),
    )
    openssl("verify", "-CAfile", str(ca_cert), "-verify_ip", host, str(cert))
    fingerprint = openssl("x509", "-in", str(ca_cert), "-noout", "-fingerprint", "-sha256").split("=", 1)[1]
    setup_url, app_url = f"http://{host}:{setup_port}/", f"https://{host}:{port}/?scan=1"
    qr = qrcode.make(setup_url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=4)
    qr.save(str(public / "connect.svg"))
    qrcode.make(setup_url, box_size=8, border=4).save(str(public / "connect.png"))
    page = (
        BOOTSTRAP.replace("{{APP_URL}}", html.escape(app_url, quote=True))
        .replace("{{SETUP_URL}}", html.escape(setup_url, quote=True))
        .replace("{{FINGERPRINT}}", fingerprint)
    )
    (public / "index.html").write_text(page)
    return {
        "host": host,
        "key": key,
        "cert": cert,
        "ca": ca_cert,
        "public": public,
        "setup_url": setup_url,
        "app_url": app_url,
        "fingerprint": fingerprint,
    }


def bootstrap_handler(public: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            files = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/connect.svg": ("connect.svg", "image/svg+xml"),
                "/docentra-ca.crt": ("docentra-ca.crt", "application/x-x509-ca-cert"),
            }
            entry = files.get(urlsplit(self.path).path)
            if not entry:
                self.send_error(404)
                return
            data = (public / entry[0]).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", entry[1])
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'",
            )
            if entry[0].endswith(".crt"):
                self.send_header("Content-Disposition", 'attachment; filename="docentra-ca.crt"')
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            pass

    return Handler


def serve(config: dict, port: int, setup_port: int):
    # This small HTTP listener only shares the public CA/guide; never app data or login.
    server = ThreadingHTTPServer((config["host"], setup_port), bootstrap_handler(config["public"]))
    environment = {**os.environ, "COOKIE_SECURE": "true"}
    log_path = config["key"].parent.parent / "api.log"
    with log_path.open("a") as log:
        log_path.chmod(0o600)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                config["host"],
                "--port",
                str(port),
                "--ssl-keyfile",
                str(config["key"]),
                "--ssl-certfile",
                str(config["cert"]),
                "--no-access-log",
                "--no-proxy-headers",
            ],
            cwd=ROOT,
            env=environment,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        try:
            context = ssl.create_default_context(cafile=str(config["ca"]))
            client = build_opener(ProxyHandler({}), HTTPSHandler(context=context))
            for _ in range(60):
                if process.poll() is not None:
                    raise RuntimeError(
                        "HTTPS API không khởi động. Xem .data/mobile/api.log; kiểm tra cổng có đang bị chiếm."
                    )
                try:
                    with client.open(f"https://{config['host']}:{port}/ready", timeout=2) as response:
                        if response.status == 200:
                            break
                except (URLError, OSError):
                    time.sleep(0.5)
            else:
                raise RuntimeError("Database/MinIO chưa ready. Chạy docker compose up -d api worker trước.")
            print(f"HTTPS ready: {config['app_url']}", flush=True)
            print(f"Kết nối Android / QR: {config['setup_url']}", flush=True)
            print(f"CA SHA-256: {config['fingerprint']}", flush=True)
            print("Giữ terminal này mở. Ctrl+C dừng cả HTTPS API và trang kết nối.", flush=True)

            def monitor():
                process.wait()
                server.shutdown()

            threading.Thread(target=monitor, daemon=True).start()
            server.serve_forever(poll_interval=0.25)
            if process.poll() not in (None, 0):
                raise RuntimeError("HTTPS API đã dừng bất thường. Xem .data/mobile/api.log.")
        finally:
            server.server_close()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


BOOTSTRAP = """<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Docentra · Kết nối điện thoại</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6ef;color:#173f34;font:16px/1.6 system-ui,sans-serif}main{max-width:900px;margin:40px auto;padding:28px}header{display:flex;align-items:center;justify-content:space-between;gap:20px}header b{font-size:28px;letter-spacing:-1px}.badge{font-size:12px;border:1px solid #ccd9c7;border-radius:20px;padding:5px 12px}h1{font-size:36px;line-height:1.2;letter-spacing:-1px;margin-bottom:15px}p{color:#566d5e}.layout{display:grid;grid-template-columns:240px 1fr;gap:32px;margin-top:30px}.card{background:white;border:1px solid #dfe6d9;border-radius:18px;padding:25px;margin-bottom:18px}.qr{width:100%;height:auto}.step{font-size:12px;letter-spacing:1px;color:#69815f;font-weight:700}h2{font-size:21px;line-height:1.35;margin:8px 0 12px}.button{display:inline-block;text-decoration:none;background:#174e3f;color:white;border-radius:9px;padding:13px 18px;font-weight:600;font-size:14px}.secondary{background:#eaf0e4;color:#174e3f}code{font-size:12px;overflow-wrap:anywhere;display:block;background:#f4f6f0;padding:12px;border-radius:8px}li{margin-bottom:9px}a{color:#174e3f}.small{font-size:12px}footer{font-size:12px;margin-top:30px;color:#64775f}@media(max-width:650px){main{padding:20px;margin:10px auto}h1{font-size:29px}.layout{grid-template-columns:1fr;gap:5px}.qr{max-width:200px}.qr-card{text-align:center}.card{padding:22px}header b{font-size:25px}}
</style></head><body><main><header><b>docentra.</b><span class="badge">Android · Cùng Wi-Fi</span></header><h1>Từ điện thoại đến hồ sơ<br>đã sẵn sàng để kiểm tra.</h1><p>Cấu hình HTTPS một lần, sau đó mở camera và chụp nhiều trang ngay tại nơi lưu giấy tờ.</p><div class="layout"><aside><section class="card qr-card"><span class="step">MỞ TRÊN ĐIỆN THOẠI</span><img class="qr" src="/connect.svg" alt="QR mở hướng dẫn kết nối Android"><p class="small">Dùng camera của điện thoại quét QR. Máy tính và điện thoại phải cùng Wi-Fi.</p><code>{{SETUP_URL}}</code></section></aside><div><section class="card"><span class="step">01 · CHỈ LẦN ĐẦU</span><h2>Tải chứng chỉ nội bộ</h2><p>Trang HTTP này chỉ chia sẻ hướng dẫn và chứng chỉ công khai. Đăng nhập và hồ sơ dùng địa chỉ HTTPS ở bước 3.</p><a class="button secondary" href="/docentra-ca.crt" download>Tải docentra-ca.crt</a><p class="small">Đối chiếu dấu vân tay này với terminal trên máy tính:</p><code>{{FINGERPRINT}}</code></section><section class="card"><span class="step">02 · TRÊN ANDROID</span><h2>Cho phép Chrome tin cậy HTTPS</h2><ol><li>Mở <b>Cài đặt → Bảo mật và quyền riêng tư → Cài đặt bảo mật khác → Mã hóa và thông tin xác thực</b>.</li><li>Chọn <b>Cài đặt chứng chỉ → Chứng chỉ CA</b>, rồi chọn file <b>docentra-ca.crt</b> vừa tải. Tên menu có thể khác theo hãng máy; tìm “Chứng chỉ CA” trong Cài đặt.</li><li>Đóng và mở lại Chrome nếu cần. Đây là CA riêng của bản demo; chỉ cài bộ chứng chỉ do máy tính của bạn tạo.</li></ol><p class="small"><a href="https://support.google.com/pixelphone/answer/2844832?hl=vi" rel="noreferrer">Hướng dẫn chứng chỉ Android của Google</a></p></section><section class="card"><span class="step">03 · BẮT ĐẦU SCAN</span><h2>Mở Docentra và cho phép camera</h2><p>Đăng nhập, chọn đúng nhân viên, nhấn <b>Mở camera</b> và cho phép Camera. Chụp → xem lại → nhận ảnh → lật trang tiếp theo. Sau khi gửi, mở máy tính để HR đối chiếu.</p><a class="button" href="{{APP_URL}}">Mở Docentra HTTPS →</a><code>{{APP_URL}}</code><p class="small">Nếu Chrome còn báo chứng chỉ không hợp lệ, kiểm tra đã cài đúng CA và IP Wi-Fi của máy tính chưa đổi. Hoàn tất cấu hình tin cậy trước khi đăng nhập.</p></section></div></div><footer>Chỉ thử bằng hồ sơ giả lập. Giữ máy tính và terminal chạy trong lúc chụp. Khi kết thúc thử nghiệm, có thể gỡ “Docentra Local Demo CA” trong danh sách chứng chỉ người dùng của Android.</footer></main></body></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=lan_host, help="IP Wi-Fi của máy tính; mặc định tự phát hiện")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--setup-port", type=int, default=8081)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not (1024 <= args.port <= 65535 and 1024 <= args.setup_port <= 65535 and args.port != args.setup_port):
        parser.error("Dùng hai cổng khác nhau trong khoảng 1024–65535")
    if not args.prepare_only and not (ROOT / "frontend/dist/index.html").exists():
        parser.error("Chạy npm --prefix frontend run build trước khi mở HTTPS")
    try:
        config = prepare(ROOT / ".data/mobile", args.host or detect_host(), args.port, args.setup_port)
        if args.prepare_only:
            print(f"Đã tạo CA, chứng chỉ HTTPS và QR tại .data/mobile; {config['setup_url']}")
        else:
            serve(config, args.port, args.setup_port)
    except KeyboardInterrupt:
        print("\nĐã dừng kết nối điện thoại.")
    except (RuntimeError, OSError, argparse.ArgumentTypeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
