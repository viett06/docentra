import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowDownToLine,
  ArrowLeft,
  BadgeCheck,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  FileText,
  History,
  LoaderCircle,
  RotateCcw,
  Save,
  ShieldCheck,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { api, errorMessage } from "../api";
import type { Doc, DocType, Field, User } from "../types";
import { Status } from "../ui";

type Props = {
  id: string;
  types: DocType[];
  user: User;
  notify: (message: string, error?: boolean) => void;
  onBack: () => void;
  onChanged: () => void;
};

export function DocumentScreen({
  id,
  types,
  user,
  notify,
  onBack,
  onChanged,
}: Props) {
  const [doc, setDoc] = useState<Doc | null>(null),
    [error, setError] = useState(""),
    [page, setPage] = useState(0),
    [zoom, setZoom] = useState(1),
    [busy, setBusy] = useState(false),
    [identity, setIdentity] = useState(false),
    [history, setHistory] = useState<
      {
        action: string;
        version: number;
        created_at: string;
        reason: string | null;
      }[]
    >([]),
    [showHistory, setShowHistory] = useState(false);
  const [reason, setReason] = useState(""),
    [reasonAction, setReasonAction] = useState<"reject" | "reopen" | null>(
      null,
    );
  useEffect(() => {
    let ignore = false;
    api<Doc>("/documents/" + id)
      .then((d) => {
        if (!ignore) {
          setDoc(d);
          setPage(0);
        }
      })
      .catch((e) => {
        if (!ignore) setError(errorMessage(e));
      });
    return () => {
      ignore = true;
    };
  }, [id]);
  const editing =
    user.role === "REVIEWER" && doc?.review_status === "NEEDS_REVIEW";
  function updateField(name: string, changes: Partial<Field>, reset = true) {
    setDoc((d) =>
      d
        ? {
            ...d,
            fields: d.fields.map((f) =>
              f.field_name === name
                ? {
                    ...f,
                    ...changes,
                    ...(reset ? { review_status: "PENDING" } : {}),
                  }
                : f,
            ),
          }
        : null,
    );
  }
  function changeType(code: string) {
    const catalog = types.find((t) => t.code === code);
    if (!catalog) return;
    setDoc((d) =>
      d
        ? {
            ...d,
            type_code: code,
            fields: Object.entries(catalog.fields).map(([field_name, spec]) => {
              const old = d.fields.find((f) => f.field_name === field_name);
              return {
                field_name,
                label: spec.label,
                field_type: spec.type,
                required: spec.required,
                value: old?.value || null,
                value_state: old?.value_state || "NOT_FOUND",
                source_page_id: old?.source_page_id || null,
                review_status: "PENDING",
                predicted_value: old?.predicted_value || null,
                confidence: old?.confidence ?? null,
              };
            }),
          }
        : null,
    );
  }
  async function save(): Promise<Doc> {
    if (!doc) throw new Error("Chưa tải được tài liệu.");
    const updated = await api<Doc>("/documents/" + id, {
      method: "PATCH",
      body: JSON.stringify({
        version: doc.version,
        type_code: doc.type_code,
        title: doc.title,
        fields: doc.fields.map((f) => ({
          field_name: f.field_name,
          value: f.value,
          value_state: f.value_state,
          source_page_id: f.source_page_id,
          reviewed: f.review_status !== "PENDING",
        })),
      }),
    });
    setDoc(updated);
    onChanged();
    return updated;
  }
  async function saveClick() {
    setBusy(true);
    try {
      await save();
      notify("Đã lưu kết quả kiểm tra và lịch sử thay đổi.");
    } catch (e) {
      notify(errorMessage(e), true);
    } finally {
      setBusy(false);
    }
  }
  async function verify() {
    if (!identity) {
      notify("Cần xác nhận đúng nhân viên trước khi duyệt.", true);
      return;
    }
    setBusy(true);
    try {
      const saved = await save();
      const verified = await api<Doc>(`/documents/${id}/verify`, {
        method: "POST",
        body: JSON.stringify({
          version: saved.version,
          identity_confirmed: true,
        }),
      });
      setDoc(verified);
      setIdentity(false);
      onChanged();
      notify("Đã xác minh tài liệu. Dữ liệu hiện có thể tra cứu trong kho.");
    } catch (e) {
      notify(errorMessage(e), true);
    } finally {
      setBusy(false);
    }
  }
  async function submitReason() {
    if (!doc || !reasonAction) return;
    setBusy(true);
    try {
      const updated = await api<Doc>(`/documents/${id}/${reasonAction}`, {
        method: "POST",
        body: JSON.stringify({ version: doc.version, reason }),
      });
      setDoc(updated);
      setReasonAction(null);
      setReason("");
      setIdentity(false);
      onChanged();
      notify(
        reasonAction === "reopen"
          ? "Đã mở lại. Tài liệu tạm rời khỏi kho tra cứu."
          : "Đã từ chối tài liệu và lưu lý do.",
      );
    } catch (e) {
      notify(errorMessage(e), true);
    } finally {
      setBusy(false);
    }
  }
  async function toggleHistory() {
    if (!showHistory) {
      try {
        setHistory(await api<typeof history>(`/documents/${id}/history`));
      } catch (e) {
        notify(errorMessage(e), true);
        return;
      }
    }
    setShowHistory(!showHistory);
  }
  if (error)
    return (
      <div className="notice error" role="alert">
        {error}
        <button className="button ghost" onClick={onBack}>
          Quay lại
        </button>
      </div>
    );
  if (!doc)
    return (
      <div className="empty">
        <LoaderCircle className="spin" />
        <p>Đang mở tài liệu và trang nguồn…</p>
      </div>
    );
  const checked = doc.fields.filter(
      (f) => f.review_status !== "PENDING",
    ).length,
    current = doc.pages[page];
  return (
    <>
      <div className="detail-heading">
        <div>
          <button className="back-button" onClick={onBack}>
            <ArrowLeft size={16} />
            Trở về danh sách
          </button>
          <div className="detail-title">
            <h1>
              {doc.title ||
                types.find((t) => t.code === doc.type_code)?.name ||
                "Tài liệu"}
            </h1>
            <Status value={doc.review_status} />
          </div>
          <p>
            <span className="employee-label">{doc.employee_code}</span>
            {doc.employee_name}
            <span>·</span>
            {doc.pages.length} trang<span>·</span>Phiên bản {doc.version}
          </p>
        </div>
        <div className="button-row">
          {user.role === "REVIEWER" && (
            <button className="button secondary" onClick={toggleHistory}>
              <History size={16} />
              Lịch sử
            </button>
          )}
          {doc.review_status === "VERIFIED" && (
            <a
              className="button secondary"
              href={`/api/v1/documents/${id}/export`}
            >
              <ArrowDownToLine size={16} />
              Xuất CSV
            </a>
          )}
          {user.role === "REVIEWER" &&
            ["VERIFIED", "REJECTED"].includes(doc.review_status) && (
              <button
                className="button secondary"
                onClick={() => setReasonAction("reopen")}
              >
                <RotateCcw size={16} />
                Mở lại kiểm tra
              </button>
            )}
        </div>
      </div>
      <div className="review-layout">
        <section className="source-viewer">
          <header>
            <span>
              <FileText size={17} />
              BẢN SCAN GỐC
            </span>
            <div>
              <button
                className="icon-button"
                aria-label="Thu nhỏ ảnh"
                onClick={() => setZoom((z) => Math.max(0.6, z - 0.15))}
              >
                <ZoomOut size={17} />
              </button>
              <span className="small">{Math.round(zoom * 100)}%</span>
              <button
                className="icon-button"
                aria-label="Phóng to ảnh"
                onClick={() => setZoom((z) => Math.min(2, z + 0.15))}
              >
                <ZoomIn size={17} />
              </button>
            </div>
          </header>
          <div className="scan-canvas">
            {current ? (
              <img
                src={current.image_url}
                alt={`Bản scan gốc, trang ${page + 1}`}
                style={{ width: `${zoom * 100}%` }}
              />
            ) : (
              <div className="empty">Chưa có trang nguồn</div>
            )}
          </div>
          <footer>
            <button
              className="icon-button"
              disabled={page === 0}
              aria-label="Trang trước"
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft size={19} />
            </button>
            <span>
              Trang <b>{page + 1}</b> / {doc.pages.length}
            </span>
            <button
              className="icon-button"
              disabled={page >= doc.pages.length - 1}
              aria-label="Trang tiếp"
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight size={19} />
            </button>
          </footer>
        </section>
        <section className="review-form">
          <div className="review-form-heading">
            <div className="review-form-icon">
              <ClipboardCheck size={22} />
            </div>
            <div>
              <h2>{editing ? "Đối chiếu thông tin" : "Thông tin tài liệu"}</h2>
              <p>
                {editing
                  ? "Đề xuất OCR cần bạn kiểm tra từng trường."
                  : "Thông tin được lưu cùng bằng chứng nguồn."}
              </p>
            </div>
          </div>
          {doc.identity_note && (
            <div
              className={
                "notice " +
                (doc.identity_match === false
                  ? "error"
                  : doc.identity_match === true
                    ? "positive"
                    : "")
              }
            >
              <span>
                {doc.identity_match === false ? (
                  <AlertTriangle size={17} />
                ) : (
                  <ShieldCheck size={17} />
                )}
              </span>
              {doc.identity_note}
            </div>
          )}
          <div className="review-basic">
            <label>
              Loại giấy tờ
              <select
                aria-label="Loại giấy tờ"
                disabled={!editing || busy}
                value={doc.type_code}
                onChange={(e) => changeType(e.target.value)}
              >
                {types.map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tên tài liệu
              <input
                value={doc.title}
                disabled={!editing || busy}
                maxLength={500}
                onChange={(e) =>
                  setDoc((d) => (d ? { ...d, title: e.target.value } : d))
                }
              />
            </label>
          </div>
          <div className="field-section-head">
            <span>TRƯỜNG DỮ LIỆU</span>
            {editing && (
              <span>
                {checked}/{doc.fields.length} đã đối chiếu
              </span>
            )}
          </div>
          {!doc.fields.length && (
            <div className="notice">
              <AlertTriangle size={18} />
              Chưa nhận diện được loại giấy tờ. Hãy chọn loại phù hợp để nhập và
              đối chiếu các trường, hoặc từ chối nếu ngoài phạm vi MVP.
            </div>
          )}
          {doc.fields.map((field) => (
            <article
              className={
                "review-field " +
                (field.review_status !== "PENDING" ? "field-checked" : "")
              }
              key={field.field_name}
            >
              <div className="field-title">
                <label htmlFor={"field-" + field.field_name}>
                  {field.label}
                  {field.required && <span title="Bắt buộc có giá trị">*</span>}
                </label>
                {field.confidence !== null ? (
                  <span
                    className={
                      "confidence " + (field.confidence < 0.8 ? "low" : "")
                    }
                  >
                    OCR {Math.round(field.confidence * 100)}%
                  </span>
                ) : (
                  <span className="confidence low">
                    {field.value_state === "NOT_FOUND"
                      ? "Chưa tìm thấy"
                      : "Nhập thủ công"}
                  </span>
                )}
              </div>
              {field.value_state === "PRESENT" ? (
                <input
                  id={"field-" + field.field_name}
                  type={field.field_type === "date" ? "date" : "text"}
                  value={field.value || ""}
                  disabled={!editing || busy}
                  maxLength={500}
                  onChange={(e) =>
                    updateField(field.field_name, {
                      value: e.target.value || null,
                      value_state: e.target.value ? "PRESENT" : "NOT_FOUND",
                    })
                  }
                />
              ) : (
                <div className="missing-value">
                  <span>
                    {field.value_state === "UNREADABLE"
                      ? "Ảnh không đọc được"
                      : field.value_state === "NOT_APPLICABLE"
                        ? "Không áp dụng"
                        : "Không tìm thấy trên tài liệu"}
                  </span>
                  {editing && (
                    <button
                      className="text-button"
                      onClick={() =>
                        updateField(field.field_name, {
                          value_state: "PRESENT",
                          value: "",
                        })
                      }
                    >
                      Nhập giá trị
                    </button>
                  )}
                </div>
              )}
              {editing && field.value_state === "PRESENT" && (
                <button
                  className="mark-missing text-button"
                  onClick={() =>
                    updateField(field.field_name, {
                      value: null,
                      value_state: "NOT_FOUND",
                      source_page_id: null,
                    })
                  }
                >
                  Đánh dấu không có trên giấy
                </button>
              )}
              <div className="field-source">
                <label>
                  <FileText size={13} />
                  Nguồn
                  <select
                    aria-label={`Trang nguồn cho ${field.label}`}
                    value={field.source_page_id || ""}
                    disabled={!editing || busy}
                    onChange={(e) => {
                      updateField(field.field_name, {
                        source_page_id: e.target.value || null,
                      });
                      const index = doc.pages.findIndex(
                        (p) => p.id === e.target.value,
                      );
                      if (index >= 0) setPage(index);
                    }}
                  >
                    <option value="">Chọn trang nguồn</option>
                    {doc.pages.map((p, i) => (
                      <option key={p.id} value={p.id}>
                        Trang {i + 1}
                      </option>
                    ))}
                  </select>
                </label>
                {field.source_page_id && (
                  <button
                    className="text-button"
                    onClick={() =>
                      setPage(
                        doc.pages.findIndex(
                          (p) => p.id === field.source_page_id,
                        ),
                      )
                    }
                  >
                    Mở trang
                    <ChevronRight size={13} />
                  </button>
                )}
              </div>
              {editing && (
                <label className="field-confirm">
                  <input
                    type="checkbox"
                    checked={field.review_status !== "PENDING"}
                    onChange={(e) =>
                      updateField(
                        field.field_name,
                        {
                          review_status: e.target.checked
                            ? "CONFIRMED"
                            : "PENDING",
                        },
                        false,
                      )
                    }
                    disabled={busy}
                  />
                  Đã đối chiếu trường này trên bản scan
                </label>
              )}
              {field.predicted_value !== null &&
                field.predicted_value !== field.value && (
                  <small className="original-value">
                    Đề xuất gốc được giữ lại: {field.predicted_value}
                  </small>
                )}
            </article>
          ))}
          {editing && (
            <>
              <label className="identity-confirm">
                <input
                  type="checkbox"
                  checked={identity}
                  onChange={(e) => setIdentity(e.target.checked)}
                />
                <span>
                  Tôi đã đối chiếu và xác nhận tài liệu thuộc đúng nhân viên{" "}
                  <b>{doc.employee_code}</b>.
                </span>
              </label>
              <div className="review-action-bar">
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={saveClick}
                >
                  <Save size={16} />
                  Lưu chỉnh sửa
                </button>
                <button
                  className="button primary"
                  disabled={
                    busy ||
                    !identity ||
                    doc.type_code === "unknown" ||
                    doc.identity_match === false
                  }
                  onClick={verify}
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : (
                    <BadgeCheck size={17} />
                  )}
                  Xác minh tài liệu
                </button>
              </div>
              <button
                className="text-button reject-button"
                disabled={busy}
                onClick={() => setReasonAction("reject")}
              >
                <X size={15} />
                Từ chối hoặc yêu cầu chụp lại
              </button>
            </>
          )}
          {doc.review_status === "VERIFIED" && (
            <div className="verified-note">
              <CheckCircle2 size={22} />
              <div>
                <b>Đã được HR xác minh</b>
                <span>
                  {doc.verified_at
                    ? new Date(doc.verified_at).toLocaleString("vi-VN")
                    : ""}
                </span>
                <small>
                  Ảnh nguồn và dữ liệu AI ban đầu được giữ riêng để truy vết.
                </small>
              </div>
            </div>
          )}
        </section>
      </div>
      {showHistory && (
        <section className="panel history-panel">
          <h2>Lịch sử của tài liệu</h2>
          {history.map((h, i) => (
            <div key={i}>
              <span className="history-dot">
                <Check size={12} />
              </span>
              <b>{h.action}</b>
              <span>Phiên bản {h.version}</span>
              <span className="muted">
                {new Date(h.created_at).toLocaleString("vi-VN")}
              </span>
              {h.reason && <p>{h.reason}</p>}
            </div>
          ))}
        </section>
      )}
      {reasonAction && (
        <div className="modal-backdrop">
          <div
            className="reason-modal"
            role="dialog"
            aria-modal="true"
            aria-label={
              reasonAction === "reopen" ? "Mở lại kiểm tra" : "Từ chối tài liệu"
            }
          >
            <header>
              <h2>
                {reasonAction === "reopen"
                  ? "Mở lại để kiểm tra"
                  : "Từ chối tài liệu"}
              </h2>
              <button
                className="icon-button"
                aria-label="Đóng"
                onClick={() => setReasonAction(null)}
              >
                <X size={20} />
              </button>
            </header>
            <p>
              {reasonAction === "reopen"
                ? "Tài liệu sẽ tạm rời khỏi kho tra cứu cho đến khi được xác minh lại."
                : "Ghi lại vấn đề để người số hóa biết cần chỉnh hoặc chụp lại điều gì."}
            </p>
            <label>
              Lý do
              <textarea
                autoFocus
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                maxLength={1000}
                placeholder="Tối thiểu 5 ký tự…"
              />
            </label>
            <footer>
              <button
                className="button secondary"
                onClick={() => setReasonAction(null)}
              >
                Hủy
              </button>
              <button
                className="button primary"
                disabled={busy || reason.trim().length < 5}
                onClick={submitReason}
              >
                Xác nhận
              </button>
            </footer>
          </div>
        </div>
      )}
    </>
  );
}
