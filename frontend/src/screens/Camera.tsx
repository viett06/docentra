import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Camera,
  Check,
  ImagePlus,
  LoaderCircle,
  RotateCcw,
  SwitchCamera,
  X,
} from "lucide-react";

function ScanDialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.showModal();
    return () => {
      document.body.style.overflow = overflow;
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className="scan-dialog"
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <header>
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Đóng cửa sổ scan"
          onClick={onClose}
        >
          <X size={23} />
        </button>
      </header>
      {children}
    </dialog>
  );
}

export function PagePreview({
  url,
  title,
  onClose,
  onRetake,
}: {
  url: string;
  title: string;
  onClose: () => void;
  onRetake?: () => void;
}) {
  return (
    <ScanDialog title={title} onClose={onClose}>
      <div className="scan-photo">
        <img src={url} alt={title} />
      </div>
      <p className="scan-tip">
        Phóng to bằng hai ngón tay để kiểm tra chữ, đủ bốn góc và không bị lóa.
      </p>
      <footer>
        {onRetake && (
          <button className="button secondary" onClick={onRetake}>
            <RotateCcw size={18} />
            Chụp lại trang này
          </button>
        )}
        <button className="button primary" onClick={onClose}>
          <Check size={18} />
          Giữ trang
        </button>
      </footer>
    </ScanDialog>
  );
}

type Props = {
  title: string;
  count: number;
  replacing: boolean;
  onAccept: (blob: Blob) => boolean;
  onClose: () => void;
  onNative: () => void;
};

export function CameraCapture({
  title,
  count,
  replacing,
  onAccept,
  onClose,
  onNative,
}: Props) {
  const video = useRef<HTMLVideoElement>(null),
    stream = useRef<MediaStream | null>(null),
    generation = useRef(0),
    alive = useRef(true),
    capturing = useRef(false);
  const [media, setMedia] = useState<MediaStream | null>(null),
    [ready, setReady] = useState(false),
    [opening, setOpening] = useState(false),
    [taking, setTaking] = useState(false),
    [error, setError] = useState("");
  const [facing, setFacing] = useState<"environment" | "user">("environment"),
    [shot, setShot] = useState<{ blob: Blob; url: string } | null>(null);
  const shotRef = useRef(shot);
  shotRef.current = shot;
  function release() {
    generation.current++;
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  }
  async function openCamera(mode: "environment" | "user" = facing) {
    release();
    const token = generation.current;
    capturing.current = false;
    setTaking(false);
    setReady(false);
    setOpening(true);
    setError("");
    setMedia(null);
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setError(
        "Camera trực tiếp cần HTTPS được thiết bị tin cậy. Mở địa chỉ HTTPS Docentra sau khi cài chứng chỉ nội bộ.",
      );
      setOpening(false);
      return;
    }
    try {
      const source = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: mode },
          width: { ideal: 2560 },
          height: { ideal: 1920 },
        },
      });
      if (!alive.current || token !== generation.current) {
        source.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = source;
      setMedia(source);
      setOpening(false);
    } catch (cause) {
      if (!alive.current || token !== generation.current) return;
      const name = cause instanceof DOMException ? cause.name : "";
      setError(
        name === "NotAllowedError"
          ? "Chrome chưa được cấp quyền camera. Mở quyền của trang web, cho phép Camera rồi thử lại."
          : name === "NotReadableError"
            ? "Camera đang được ứng dụng khác sử dụng. Đóng ứng dụng đó rồi thử lại."
            : name === "NotFoundError"
              ? "Không tìm thấy camera. Bạn có thể chọn ảnh hoặc dùng camera của máy."
              : "Chưa mở được camera. Kiểm tra quyền truy cập, chứng chỉ HTTPS và thử lại.",
      );
      setOpening(false);
    }
  }
  useEffect(() => {
    alive.current = true;
    void openCamera("environment");
    const pause = () => {
      if (document.hidden) {
        release();
        setMedia(null);
        setReady(false);
        setOpening(false);
        setError(
          "Camera đã tạm dừng khi bạn chuyển ứng dụng. Ảnh đã nhận vẫn được giữ trong phiên.",
        );
      }
    };
    document.addEventListener("visibilitychange", pause);
    return () => {
      alive.current = false;
      release();
      document.removeEventListener("visibilitychange", pause);
      if (shotRef.current) URL.revokeObjectURL(shotRef.current.url);
    };
  }, []);
  useEffect(() => {
    if (video.current && media && !shot) {
      video.current.srcObject = media;
      void video.current.play().catch(() => {
        if (alive.current) setError("Chạm Mở lại camera để bắt đầu xem trước.");
      });
    }
  }, [media, shot]);
  function retake() {
    if (shot) URL.revokeObjectURL(shot.url);
    setShot(null);
    setReady(false);
    if (!stream.current) void openCamera();
  }
  function snap() {
    const source = video.current;
    if (
      !source ||
      !ready ||
      capturing.current ||
      !source.videoWidth ||
      !source.videoHeight
    )
      return;
    capturing.current = true;
    setTaking(true);
    const token = generation.current,
      canvas = document.createElement("canvas");
    canvas.width = source.videoWidth;
    canvas.height = source.videoHeight;
    canvas.getContext("2d")?.drawImage(source, 0, 0);
    canvas.toBlob(
      (blob) => {
        capturing.current = false;
        if (!alive.current || token !== generation.current) return;
        setTaking(false);
        if (blob) setShot({ blob, url: URL.createObjectURL(blob) });
        else setError("Chưa tạo được ảnh. Vui lòng chụp lại.");
      },
      "image/jpeg",
      0.94,
    );
  }
  function accept(keepShooting: boolean) {
    if (!shot || !onAccept(shot.blob)) return;
    URL.revokeObjectURL(shot.url);
    setShot(null);
    setReady(false);
    if (!keepShooting) onClose();
    else if (!stream.current) void openCamera();
  }
  return (
    <ScanDialog
      title={replacing ? "Chụp lại trang" : "Scan tài liệu"}
      onClose={onClose}
    >
      <div className="scan-context">
        <span>{title}</span>
        <strong>{count}/30 trang</strong>
      </div>
      <div className={"scan-viewfinder" + (shot ? " reviewing" : "")}>
        {shot ? (
          <img src={shot.url} alt="Ảnh vừa chụp, chưa thêm vào phiên" />
        ) : (
          <>
            <video
              ref={video}
              autoPlay
              playsInline
              muted
              onCanPlay={() => setReady(true)}
            />
            {!error && <span className="scan-guide" aria-hidden="true" />}
            {opening && (
              <div className="scan-camera-status">
                <LoaderCircle size={30} className="spin" />
                <span>Đang mở camera…</span>
              </div>
            )}
          </>
        )}
      </div>
      {shot ? (
        <>
          <p className="scan-tip">
            Chữ rõ, đủ bốn góc, không bị lóa?{" "}
            {replacing
              ? "Nhận ảnh sẽ thay đúng trang cũ, giữ nguyên thứ tự."
              : "Nhận ảnh rồi lật sang trang tiếp theo."}
          </p>
          <footer className="scan-review-actions">
            <button className="button secondary" onClick={retake}>
              <RotateCcw size={18} />
              Chụp lại
            </button>
            <button className="button primary" onClick={() => accept(false)}>
              <Check size={18} />
              {replacing ? "Thay trang cũ" : "Nhận & xong"}
            </button>
            {!replacing && count < 29 && (
              <button className="button primary" onClick={() => accept(true)}>
                <Camera size={18} />
                Nhận & chụp tiếp
              </button>
            )}
          </footer>
        </>
      ) : (
        <>
          {error ? (
            <div className="scan-camera-error" role="alert">
              <p>{error}</p>
              <button
                className="button secondary"
                disabled={opening}
                onClick={() => {
                  capturing.current = false;
                  setTaking(false);
                  void openCamera();
                }}
              >
                Mở lại camera
              </button>
              <button className="text-button" onClick={onNative}>
                <ImagePlus size={18} />
                Dùng camera của máy
              </button>
              <small>
                Camera của máy có thể lưu ảnh vào thư viện tùy thiết bị.
              </small>
            </div>
          ) : (
            <p className="scan-tip">
              Đặt giấy trên nền phẳng, lấy trọn bốn góc. Khung là hướng dẫn căn
              giấy, ảnh giữ toàn bộ vùng camera.
            </p>
          )}
          <footer className="scan-live-actions">
            <button
              className="icon-button"
              aria-label="Đổi camera trước hoặc sau"
              disabled={opening || taking || !!error}
              onClick={() => {
                const mode = facing === "environment" ? "user" : "environment";
                setFacing(mode);
                void openCamera(mode);
              }}
            >
              <SwitchCamera size={25} />
            </button>
            <button
              className="scan-shutter"
              aria-label="Chụp trang"
              disabled={
                !ready || opening || taking || (count >= 30 && !replacing)
              }
              onClick={snap}
            >
              {taking ? (
                <LoaderCircle className="spin" size={25} />
              ) : (
                <Camera size={29} />
              )}
            </button>
            <button className="button secondary" onClick={onClose}>
              Xong
            </button>
          </footer>
        </>
      )}
    </ScanDialog>
  );
}
