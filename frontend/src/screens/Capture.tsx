import { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Camera,
  Check,
  CheckCircle2,
  ChevronDown,
  FileImage,
  FilePlus2,
  ImagePlus,
  LoaderCircle,
  Plus,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { api, errorMessage } from "../api";
import { CameraCapture, PagePreview } from "./Camera";
import type { CaptureSession, DocType, Employee, Receipt } from "../types";

type Page = { id: string; blob: Blob; url: string; name: string };
type Group = { id: string; title: string; pages: Page[] };
type Props = {
  active: boolean;
  employees: Employee[];
  types: DocType[];
  notify: (message: string, error?: boolean) => void;
  onDone: () => void;
  onReview?: () => void;
};
const newGroup = (): Group => ({
  id: crypto.randomUUID(),
  title: "",
  pages: [],
});

export function Capture({
  active,
  employees,
  types,
  notify,
  onDone,
  onReview,
}: Props) {
  const [employee, setEmployee] = useState(""),
    [groups, setGroups] = useState<Group[]>(() => [newGroup()]),
    [cameraTarget, setCameraTarget] = useState<{
      groupId: string;
      pageId?: string;
    } | null>(null),
    [preview, setPreview] = useState<{
      groupId: string;
      pageId: string;
    } | null>(null),
    [preparing, setPreparing] = useState(false);
  const [phase, setPhase] = useState<
      "edit" | "uploading" | "processing" | "success"
    >("edit"),
    [locked, setLocked] = useState(false),
    [progress, setProgress] = useState(""),
    [error, setError] = useState(""),
    [sample, setSample] = useState("employment_contract");
  const input = useRef<HTMLInputElement>(null),
    nativeInput = useRef<HTMLInputElement>(null),
    fileTarget = useRef<{ groupId: string; pageId?: string }>({ groupId: "" }),
    mounted = useRef(true),
    groupRef = useRef(groups);
  const sessionKey = useRef(crypto.randomUUID()),
    processKey = useRef(crypto.randomUUID()),
    sessionId = useRef("");
  groupRef.current = groups;
  const total = groups.reduce((count, g) => count + g.pages.length, 0),
    busy = phase === "uploading" || phase === "processing";
  useEffect(() => {
    if (!employee && employees.length) setEmployee(employees[0].id);
  }, [employees, employee]);
  useEffect(
    () => () => {
      mounted.current = false;
      groupRef.current.forEach((g) =>
        g.pages.forEach((p) => URL.revokeObjectURL(p.url)),
      );
    },
    [],
  );
  useEffect(() => {
    if (!active) {
      setCameraTarget(null);
      setPreview(null);
    }
  }, [active]);
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (total > 0 && phase !== "success") {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [total, phase]);
  function addPages(
    groupId: string,
    blobs: { blob: Blob; name: string }[],
    pageId?: string,
  ): boolean {
    if (locked || !mounted.current) return false;
    const current = groupRef.current;
    const group = current.find((g) => g.id === groupId);
    if (!group || (pageId && !group.pages.some((p) => p.id === pageId)))
      return false;
    const count = current.reduce((n, g) => n + g.pages.length, 0);
    if (count + blobs.length - (pageId ? 1 : 0) > 30) {
      notify("Mỗi phiên nhận tối đa 30 trang. Hãy chia nhỏ phiên scan.", true);
      return false;
    }
    const pages = blobs.map(({ blob, name }) => ({
      id: crypto.randomUUID(),
      blob,
      name,
      url: URL.createObjectURL(blob),
    }));
    if (pageId)
      URL.revokeObjectURL(group.pages.find((p) => p.id === pageId)!.url);
    setGroups((gs) =>
      gs.map((g) =>
        g.id !== groupId
          ? g
          : {
              ...g,
              pages: pageId
                ? g.pages.flatMap((p) => (p.id === pageId ? pages : [p]))
                : [...g.pages, ...pages],
            },
      ),
    );
    return true;
  }
  function remove(groupId: string, page: Page) {
    URL.revokeObjectURL(page.url);
    setGroups((gs) =>
      gs.map((g) =>
        g.id === groupId
          ? { ...g, pages: g.pages.filter((p) => p.id !== page.id) }
          : g,
      ),
    );
  }
  function reorder(groupId: string, index: number, direction: number) {
    setGroups((gs) =>
      gs.map((g) => {
        if (g.id !== groupId) return g;
        const pages = [...g.pages];
        [pages[index], pages[index + direction]] = [
          pages[index + direction],
          pages[index],
        ];
        return { ...g, pages };
      }),
    );
  }
  function chooseFile(groupId: string, pageId?: string, native = false) {
    fileTarget.current = { groupId, pageId };
    const control = native ? nativeInput.current : input.current;
    if (control) {
      control.multiple = !native && !pageId;
      control.value = "";
      control.click();
    }
  }
  function startCamera(groupId: string, pageId?: string) {
    if (locked || preparing) return;
    setPreview(null);
    setCameraTarget({ groupId, pageId });
  }
  async function receiveFiles(files: File[]) {
    if (!files.length || preparing || locked) return;
    const destination = { ...fileTarget.current };
    setPreparing(true);
    try {
      if (destination.pageId && files.length !== 1)
        throw new Error("Chọn một ảnh để thay trang cũ.");
      if (files.length + total - (destination.pageId ? 1 : 0) > 30)
        throw new Error("Mỗi phiên nhận tối đa 30 trang.");
      for (const file of files) {
        if (file.size > 10 * 1024 * 1024)
          throw new Error("Một ảnh lớn hơn 10 MB. Hãy chọn ảnh nhỏ hơn.");
        if (
          file.type &&
          !["image/jpeg", "image/png", "image/webp"].includes(file.type)
        )
          throw new Error(
            "Chọn ảnh JPEG, PNG hoặc WebP. Định dạng ảnh này chưa được hỗ trợ.",
          );
        const url = URL.createObjectURL(file),
          image = new Image();
        try {
          image.src = url;
          await image.decode();
          if (image.naturalWidth * image.naturalHeight > 24_000_000)
            throw new Error(
              "Ảnh vượt quá 24 megapixel. Hãy giảm độ phân giải camera.",
            );
        } catch (cause) {
          throw new Error(
            cause instanceof Error && cause.message.includes("24 megapixel")
              ? cause.message
              : "Không đọc được ảnh. Hãy chọn JPEG, PNG hoặc WebP hợp lệ.",
          );
        } finally {
          URL.revokeObjectURL(url);
        }
      }
      addPages(
        destination.groupId,
        files.map((f) => ({ blob: f, name: f.name })),
        destination.pageId,
      );
    } catch (cause) {
      notify(errorMessage(cause), true);
    } finally {
      if (mounted.current) setPreparing(false);
    }
  }
  async function loadSample() {
    if (!employee || locked || preparing) return;
    setPreparing(true);
    try {
      const count = sample === "employment_contract" ? 2 : 1;
      const blobs = [];
      for (let p = 1; p <= count; p++) {
        const response = await fetch(
          `/api/v1/demo/samples/${employee}/${sample}/${p}?page_count=${count}`,
          { cache: "no-store" },
        );
        if (!response.ok) throw new Error("Không tải được dữ liệu giả lập.");
        blobs.push({
          blob: await response.blob(),
          name: `Mẫu giả lập · Trang ${p}`,
        });
      }
      const empty = groups.find((g) => g.pages.length === 0);
      if (empty) {
        addPages(empty.id, blobs);
        setGroups((gs) =>
          gs.map((g) =>
            g.id === empty.id
              ? {
                  ...g,
                  title:
                    types.find((t) => t.code === sample)?.name ||
                    "Tài liệu chưa xác định",
                }
              : g,
          ),
        );
      } else {
        const group = newGroup();
        group.title =
          types.find((t) => t.code === sample)?.name ||
          "Tài liệu chưa xác định";
        group.pages = blobs.map(({ blob, name }) => ({
          id: crypto.randomUUID(),
          blob,
          name,
          url: URL.createObjectURL(blob),
        }));
        if (total + group.pages.length > 30)
          throw new Error("Đã đạt giới hạn trang của phiên.");
        setGroups((gs) => [...gs, group]);
      }
      notify("Đã thêm ảnh giấy tờ giả lập. Ảnh vẫn đi qua OCR thực sự.");
    } catch (e) {
      notify(errorMessage(e), true);
    } finally {
      if (mounted.current) setPreparing(false);
    }
  }
  function clearPages() {
    groupRef.current.forEach((g) =>
      g.pages.forEach((p) => URL.revokeObjectURL(p.url)),
    );
    setGroups([newGroup()]);
  }
  function reset() {
    clearPages();
    sessionKey.current = crypto.randomUUID();
    processKey.current = crypto.randomUUID();
    sessionId.current = "";
    setLocked(false);
    setPhase("edit");
    setError("");
    setProgress("");
  }
  async function poll(id: string) {
    setPhase("processing");
    for (;;) {
      if (!mounted.current) return;
      const row = await api<CaptureSession>("/scan-sessions/" + id);
      setProgress(
        row.job?.status === "QUEUED"
          ? `Đang chờ worker · lần ${row.job.attempt_count + 1}/${row.job.max_attempts}`
          : `OCR, phân loại và trích xuất ${row.pages.length} trang…`,
      );
      if (row.job?.status === "SUCCEEDED") {
        setPhase("success");
        clearPages();
        onDone();
        return;
      }
      if (row.job?.status === "FAILED")
        throw new Error(
          "Xử lý chưa thành công (" +
            (row.job.error_code || "UNKNOWN") +
            "). Ảnh đã được lưu; có thể gửi yêu cầu chạy lại.",
        );
      await new Promise((r) => window.setTimeout(r, 1500));
    }
  }
  async function send() {
    if (!employee || total === 0) {
      notify("Chọn nhân viên và thêm ít nhất một trang.", true);
      return;
    }
    setError("");
    setLocked(true);
    setPhase("uploading");
    setCameraTarget(null);
    setPreview(null);
    try {
      const created = await api<CaptureSession>("/scan-sessions", {
        method: "POST",
        body: JSON.stringify({
          employee_id: employee,
          client_session_id: sessionKey.current,
        }),
      });
      sessionId.current = created.id;
      if (
        created.job &&
        ["QUEUED", "RUNNING", "SUCCEEDED"].includes(created.job.status)
      ) {
        await poll(created.id);
        return;
      }
      const receipts: Receipt[] = [];
      const mapping = new Map<string, string>();
      let index = 0;
      for (const group of groups) {
        for (const page of group.pages) {
          index++;
          setProgress(`Đang gửi trang ${index}/${total} đến kho private…`);
          const form = new FormData();
          form.append("client_page_id", page.id);
          form.append("page_order", String(index));
          form.append("file", page.blob, "capture");
          const receipt = await api<Receipt>(
            `/scan-sessions/${created.id}/pages`,
            { method: "POST", body: form },
          );
          receipts.push(receipt);
          mapping.set(page.id, receipt.id);
        }
      }
      await api(`/scan-sessions/${created.id}/finalize`, {
        method: "POST",
        body: JSON.stringify({
          version: created.version,
          pages: receipts.map((p) => ({ id: p.id, sha256: p.sha256 })),
        }),
      });
      if (created.job?.status === "FAILED")
        processKey.current = crypto.randomUUID();
      await api(`/scan-sessions/${created.id}/process`, {
        method: "POST",
        body: JSON.stringify({
          idempotency_key: processKey.current,
          groups: groups
            .filter((g) => g.pages.length)
            .map((g) => ({
              title: g.title,
              page_ids: g.pages.map((p) => mapping.get(p.id)),
            })),
        }),
      });
      await poll(created.id);
    } catch (e) {
      setPhase("edit");
      setError(errorMessage(e));
      notify(errorMessage(e), true);
    }
  }

  if (phase === "success")
    return (
      <div className="capture-success">
        <span className="success-circle">
          <CheckCircle2 size={44} />
        </span>
        <span className="eyebrow text-muted">ĐÃ HOÀN TẤT XỬ LÝ</span>
        <h1>Tài liệu đã đến đúng nơi.</h1>
        <p>
          Ảnh gốc được lưu trong kho private. Kết quả OCR và các đề xuất đang
          chờ HR đối chiếu, chưa được công bố vào kho tra cứu.
        </p>
        <div className="success-steps">
          <span>
            <Check size={16} />
            Ảnh đã lưu
          </span>
          <span>
            <Check size={16} />
            OCR hoàn tất
          </span>
          <span>
            <Check size={16} />
            Chờ HR kiểm tra
          </span>
        </div>
        <div className="button-row">
          {onReview && (
            <button className="button primary" onClick={onReview}>
              Kiểm tra tài liệu
              <ArrowRight size={17} />
            </button>
          )}
          <button
            className={"button " + (onReview ? "secondary" : "primary")}
            onClick={reset}
          >
            <Plus size={18} />
            Tạo phiên scan tiếp theo
          </button>
        </div>
      </div>
    );
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow text-muted">BẮT ĐẦU TỪ TRANG GIẤY</div>
          <h1>Số hóa ngay tại nơi lưu hồ sơ.</h1>
          <p>
            Một nhân viên mỗi phiên. Một giấy tờ mỗi nhóm. Giữ đúng thứ tự và đủ
            trang.
          </p>
        </div>
        <span className="step-counter">
          <b>01</b> Chụp & gửi <ChevronDown size={14} />
        </span>
      </div>
      <div className="capture-layout">
        <div>
          <section className="panel capture-employee">
            <div className="section-number">01</div>
            <div>
              <h3>Chọn đúng hồ sơ nhân viên</h3>
              <p>
                Đối chiếu mã với tập giấy trước khi chụp để tránh gắn nhầm
                người.
              </p>
              <select
                aria-label="Nhân viên cần số hóa"
                value={employee}
                disabled={locked || preparing}
                onChange={(e) => setEmployee(e.target.value)}
              >
                <option value="">Chọn nhân viên…</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.employee_code} · {e.full_name}
                  </option>
                ))}
              </select>
            </div>
          </section>
          <div className="capture-section-title">
            <span>
              <b>02</b>Chụp và sắp xếp tài liệu
            </span>
            <span className="small muted">{total}/30 trang</span>
          </div>
          {groups.map((group, groupIndex) => (
            <section className="panel capture-group" key={group.id}>
              <div className="capture-group-head">
                <span className="file-icon">
                  <FileImage size={19} />
                </span>
                <label>
                  <span className="small muted">
                    TÀI LIỆU {String(groupIndex + 1).padStart(2, "0")}
                  </span>
                  <input
                    placeholder="Tên gợi nhớ (AI sẽ phân loại từ ảnh)"
                    value={group.title}
                    disabled={locked || preparing}
                    onChange={(e) =>
                      setGroups((gs) =>
                        gs.map((g) =>
                          g.id === group.id
                            ? { ...g, title: e.target.value }
                            : g,
                        ),
                      )
                    }
                  />
                </label>
                {groups.length > 1 && !locked && (
                  <button
                    className="icon-button danger"
                    title="Bỏ nhóm tài liệu"
                    aria-label="Bỏ nhóm tài liệu"
                    disabled={preparing}
                    onClick={() => {
                      group.pages.forEach((p) => URL.revokeObjectURL(p.url));
                      setGroups((gs) => gs.filter((g) => g.id !== group.id));
                    }}
                  >
                    <Trash2 size={17} />
                  </button>
                )}
              </div>
              {group.pages.length ? (
                <div className="page-thumbnails">
                  {group.pages.map((page, index) => (
                    <div className="page-thumb" key={page.id}>
                      <button
                        className="page-open"
                        aria-label={`Xem trang ${index + 1} của tài liệu ${groupIndex + 1}`}
                        onClick={() =>
                          setPreview({ groupId: group.id, pageId: page.id })
                        }
                      >
                        <img
                          src={page.url}
                          alt={`Trang ${index + 1} của tài liệu ${groupIndex + 1}`}
                        />
                      </button>
                      <span className="page-index">{index + 1}</span>
                      <div className="page-thumb-tools">
                        <button
                          disabled={locked || preparing || index === 0}
                          onClick={() => reorder(group.id, index, -1)}
                          aria-label="Đưa trang lên trước"
                        >
                          <ArrowUp size={14} />
                        </button>
                        <button
                          disabled={
                            locked ||
                            preparing ||
                            index === group.pages.length - 1
                          }
                          onClick={() => reorder(group.id, index, 1)}
                          aria-label="Đưa trang ra sau"
                        >
                          <ArrowDown size={14} />
                        </button>
                        <button
                          disabled={locked || preparing}
                          onClick={() => startCamera(group.id, page.id)}
                          aria-label={`Chụp lại trang ${index + 1} của tài liệu ${groupIndex + 1}`}
                        >
                          <RotateCcw size={14} />
                        </button>
                        <button
                          disabled={locked || preparing}
                          onClick={() => remove(group.id, page)}
                          aria-label="Bỏ trang"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {!locked && (
                    <button
                      className="add-page"
                      disabled={preparing || total >= 30}
                      onClick={() => chooseFile(group.id)}
                    >
                      <ImagePlus size={25} />
                      <span>Thêm trang</span>
                    </button>
                  )}
                </div>
              ) : (
                <div className="capture-drop">
                  <span className="capture-drop-icon">
                    <ScanLine size={32} />
                  </span>
                  <h3>Một trang giấy. Một bước nhẹ hơn.</h3>
                  <p>Đặt giấy trên nền phẳng, lấy trọn bốn góc và đủ sáng.</p>
                  <div className="button-row">
                    <button
                      className="button primary"
                      disabled={!employee || locked || preparing}
                      onClick={() => startCamera(group.id)}
                    >
                      <Camera size={17} />
                      Mở camera
                    </button>
                    <button
                      className="button secondary"
                      disabled={!employee || locked || preparing}
                      onClick={() => chooseFile(group.id)}
                    >
                      <ImagePlus size={17} />
                      Chọn ảnh
                    </button>
                  </div>
                  <small>
                    JPEG, PNG, WebP · Tối đa 10 MB/ảnh · Tối đa 24 megapixel
                  </small>
                </div>
              )}
              {group.pages.length > 0 && !locked && (
                <div className="capture-group-footer">
                  <button
                    className="text-button"
                    onClick={() => startCamera(group.id)}
                  >
                    <Camera size={16} />
                    Chụp thêm trang
                  </button>
                  <span className="small muted">
                    Chạm ảnh để xem rõ hoặc chụp lại đúng vị trí trang.
                  </span>
                </div>
              )}
            </section>
          ))}
          {!locked && (
            <button
              className="add-document"
              disabled={preparing || total >= 30}
              onClick={() => setGroups((gs) => [...gs, newGroup()])}
            >
              <FilePlus2 size={19} />
              Thêm giấy tờ khác trong cùng hồ sơ
              <Plus size={17} />
            </button>
          )}
        </div>
        <aside className="capture-summary">
          <section className="panel summary-card">
            <span className="eyebrow text-muted">TRƯỚC KHI GỬI</span>
            <h3>Kiểm tra một lần nữa.</h3>
            <ul className="checklist">
              <li>
                <CheckCircle2 size={17} />
                Đúng mã nhân viên trên giấy
              </li>
              <li>
                <CheckCircle2 size={17} />
                Mỗi giấy tờ nằm trong một nhóm
              </li>
              <li>
                <CheckCircle2 size={17} />
                Đủ trang, rõ chữ, đúng thứ tự
              </li>
            </ul>
            <div className="summary-count">
              <span>
                Nhóm tài liệu
                <strong>{groups.filter((g) => g.pages.length).length}</strong>
              </span>
              <span>
                Tổng số trang<strong>{total}</strong>
              </span>
            </div>
            {error && (
              <div className="notice error" role="alert">
                {error}
              </div>
            )}
            {busy && (
              <div className="processing-notice">
                <LoaderCircle className="spin" size={22} />
                <div>
                  <b>
                    {phase === "uploading"
                      ? "Đang gửi ảnh"
                      : "Đang xử lý thực tế"}
                  </b>
                  <small>{progress}</small>
                </div>
              </div>
            )}
            <button
              className="button primary full"
              disabled={busy || preparing || !total || !employee}
              onClick={send}
            >
              {busy ? (
                <LoaderCircle className="spin" size={18} />
              ) : (
                <UploadCloud size={18} />
              )}
              <span>
                {busy
                  ? "Vui lòng giữ tab mở"
                  : error
                    ? "Thử gửi lại"
                    : "Gửi & xử lý tài liệu"}
              </span>
              {!busy && <ArrowRight size={16} />}
            </button>
            {locked && !busy && (
              <button className="button ghost full" onClick={reset}>
                <RotateCcw size={15} />
                Bắt đầu phiên mới
              </button>
            )}
            <p className="summary-privacy">
              <ShieldCheck size={16} />
              Ứng dụng giữ ảnh chờ gửi trong bộ nhớ tab, không chủ động lưu vào
              thư viện hoặc bộ nhớ offline. Đóng tab trước khi gửi có thể làm
              mất ảnh chờ.
            </p>
          </section>
          <section className="demo-sample">
            <span className="mini-label">THỬ MVP BẰNG DỮ LIỆU GIẢ</span>
            <h3>Chưa có giấy tờ mẫu?</h3>
            <p>
              Thêm ảnh giả lập cho nhân viên đang chọn, sau đó gửi qua đúng
              pipeline OCR.
            </p>
            <select
              aria-label="Loại mẫu giả lập"
              value={sample}
              disabled={locked || preparing}
              onChange={(e) => setSample(e.target.value)}
            >
              {types.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.name}
                </option>
              ))}
            </select>
            <button
              className="button secondary full"
              disabled={!employee || locked || preparing}
              onClick={loadSample}
            >
              <Plus size={16} />
              Thêm tài liệu mẫu
            </button>
          </section>
        </aside>
      </div>
      <div className="mobile-scan-bar">
        <div>
          <strong>{total} trang</strong>
          <small>
            {groups.filter((g) => g.pages.length).length} tài liệu ·{" "}
            {preparing ? "Đang kiểm tra ảnh…" : "Ảnh chờ gửi trong tab"}
          </small>
        </div>
        <button
          className="button primary"
          disabled={busy || preparing || !total || !employee}
          onClick={send}
        >
          {busy ? (
            <LoaderCircle size={18} className="spin" />
          ) : (
            <UploadCloud size={18} />
          )}
          {busy ? "Đang xử lý…" : error ? "Thử gửi lại" : "Gửi & xử lý"}
        </button>
      </div>
      <input
        ref={input}
        tabIndex={-1}
        aria-hidden="true"
        className="visually-hidden"
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        onChange={(e) => {
          void receiveFiles([...(e.target.files || [])]);
        }}
      />
      <input
        ref={nativeInput}
        tabIndex={-1}
        aria-hidden="true"
        className="visually-hidden"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        onChange={(e) => {
          void receiveFiles([...(e.target.files || [])]);
        }}
      />
      {preview &&
        (() => {
          const group = groups.find((g) => g.id === preview.groupId),
            index =
              group?.pages.findIndex((p) => p.id === preview.pageId) ?? -1;
          const page = group?.pages[index];
          return (
            page && (
              <PagePreview
                url={page.url}
                title={`Trang ${index + 1} · ${group?.title || "Tài liệu"}`}
                onClose={() => setPreview(null)}
                onRetake={
                  !locked && !preparing
                    ? () => startCamera(preview.groupId, preview.pageId)
                    : undefined
                }
              />
            )
          );
        })()}
      {cameraTarget && (
        <CameraCapture
          title={
            groups.find((g) => g.id === cameraTarget.groupId)?.title ||
            "Tài liệu đang chụp"
          }
          count={total}
          replacing={!!cameraTarget.pageId}
          onClose={() => setCameraTarget(null)}
          onNative={() => {
            chooseFile(cameraTarget.groupId, cameraTarget.pageId, true);
            setCameraTarget(null);
          }}
          onAccept={(blob) =>
            addPages(
              cameraTarget.groupId,
              [
                {
                  blob,
                  name: "Trang chụp " + new Date().toLocaleTimeString("vi-VN"),
                },
              ],
              cameraTarget.pageId,
            )
          }
        />
      )}
    </>
  );
}
