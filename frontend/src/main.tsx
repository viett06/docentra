import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  Bell,
  Check,
  ChevronRight,
  ClipboardCheck,
  FileCheck2,
  FileClock,
  FileText,
  FolderClosed,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  ScanLine,
  Users,
  X,
} from "lucide-react";
import { api, errorMessage, setCsrf } from "./api";
import type { DocType, Employee, Row, Stats, User } from "./types";
import { Capture } from "./screens/Capture";
import { DocumentScreen } from "./screens/Document";
import { Status } from "./ui";
import "./styles.css";

type Tab = "overview" | "capture" | "review" | "library" | "audit";
type Notify = (message: string, error?: boolean) => void;
export function Brand() {
  return (
    <div className="brand">
      <span className="brand-icon">
        <FolderClosed size={23} strokeWidth={2} />
        <span />
      </span>
      <span>
        docentra<span className="brand-dot">.</span>
      </span>
    </div>
  );
}
function Empty({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <FolderClosed size={29} />
      </span>
      <h3>{title}</h3>
      <p>{detail}</p>
      {action}
    </div>
  );
}
function date(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(value));
}

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState(() =>
      new URLSearchParams(window.location.search).get("scan") === "1"
        ? "capture@docentra.local"
        : "reviewer@docentra.local",
    ),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<{ user: User; csrf_token: string }>(
        "/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
      );
      setCsrf(result.csrf_token);
      onLogin(result.user);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login">
      <section className="login-story">
        <Brand />
        <div className="login-story-body">
          <span className="eyebrow">
            <span /> KHÔNG GIAN HỒ SƠ THÔNG MINH
          </span>
          <h1>
            Hồ sơ gọn hơn.
            <br />
            {" Công việc nhẹ hơn."}
          </h1>
          <p>
            Từ những trang giấy rời rạc đến dữ liệu có thể tìm thấy, kiểm chứng
            và sử dụng.
          </p>
          <div className="paper-stack">
            <div className="paper-back" />
            <div className="paper-front">
              <div className="paper-tag">
                <FileText size={18} /> HỒ SƠ NHÂN SỰ
              </div>
              <div className="paper-lines">
                <i />
                <i />
                <i />
              </div>
              <div className="paper-approved">
                <BadgeCheck size={20} />
                <div>
                  Đã xác minh<span>Luôn có trang nguồn để đối chiếu</span>
                </div>
              </div>
            </div>
            <span className="floating-scan">
              <ScanLine size={24} />
            </span>
          </div>
          <div className="story-steps">
            <span>01 Chụp & gửi</span>
            <ArrowRight size={15} />
            <span>02 Xác minh</span>
            <ArrowRight size={15} />
            <span>03 Tra cứu</span>
          </div>
        </div>
        <p className="login-footer">
          Được thiết kế cho công việc tỉ mỉ của phòng Nhân sự.
        </p>
      </section>
      <section className="login-form">
        <div className="login-form-inner">
          <span className="pill">
            <ShieldCheck size={14} /> Môi trường thử nghiệm
          </span>
          <h2>Chào mừng trở lại</h2>
          <p>Đăng nhập để tiếp tục với không gian Docentra.</p>
          <form onSubmit={submit}>
            <label>
              Email
              <input
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>
            <label>
              Mật khẩu
              <input
                type="password"
                autoComplete="current-password"
                placeholder="Nhập mật khẩu của bạn"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && (
              <div className="notice error" role="alert">
                {error}
              </div>
            )}
            <button className="button primary full" disabled={busy}>
              {busy ? "Đang đăng nhập…" : "Vào không gian làm việc"}
              <ArrowRight size={17} />
            </button>
          </form>
          <div className="demo-login">
            <span>CHỌN VAI TRÒ DEMO</span>
            <div>
              {[
                ["reviewer", "HR kiểm tra"],
                ["capture", "Người số hóa"],
                ["viewer", "Người tra cứu"],
              ].map(([id, name]) => (
                <button
                  key={id}
                  onClick={() => setEmail(id + "@docentra.local")}
                  className={email.startsWith(id + "@") ? "selected" : ""}
                >
                  {name}
                </button>
              ))}
            </div>
            <p>
              Tài khoản demo chỉ có dữ liệu giả lập. Mật khẩu được cấu hình
              trong <code>DEMO_PASSWORD</code> của dự án.
            </p>
          </div>
        </div>
        <p className="privacy-note">
          <ShieldCheck size={15} /> Ảnh scan được lưu trong kho private của môi
          trường demo.
        </p>
      </section>
    </main>
  );
}

function Table({
  rows,
  onOpen,
}: {
  rows: Row[];
  onOpen: (id: string) => void;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>TÀI LIỆU</th>
            <th>NHÂN VIÊN</th>
            <th>TRẠNG THÁI</th>
            <th>NGÀY TẠO</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} onClick={() => onOpen(r.id)}>
              <td>
                <button
                  className="table-file"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpen(r.id);
                  }}
                >
                  <span className={"file-icon type-" + r.type_code}>
                    <FileText size={19} />
                  </span>
                  <span>
                    {r.title}
                    <small>
                      {r.type_name} · {r.page_count} trang
                    </small>
                  </span>
                </button>
              </td>
              <td>
                <span className="employee-name">{r.employee_name}</span>
                <small>{r.employee_code}</small>
              </td>
              <td>
                <Status value={r.review_status} />
              </td>
              <td className="muted">{date(r.created_at)}</td>
              <td>
                <ChevronRight size={17} className="muted" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Overview({
  stats,
  rows,
  onCapture,
  onReview,
  onOpen,
  user,
}: {
  stats: Stats;
  rows: Row[];
  onCapture: () => void;
  onReview: () => void;
  onOpen: (id: string) => void;
  user: User;
}) {
  const verified = stats.documents.VERIFIED || 0,
    pending = stats.documents.NEEDS_REVIEW || 0,
    canCapture = ["CAPTURE", "REVIEWER"].includes(user.role);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow text-muted">KHÔNG GIAN NHÂN SỰ</div>
          <h1>
            Mỗi hồ sơ, một nơi rõ ràng<span className="heading-dot">.</span>
          </h1>
          <p>
            Theo dõi hành trình số hóa và giữ thông tin luôn có thể kiểm chứng.
          </p>
        </div>
        {canCapture && (
          <button className="button primary" onClick={onCapture}>
            <Plus size={18} />
            Phiên scan mới
          </button>
        )}
      </div>
      <section className="stat-grid">
        {[
          {
            label: "Hồ sơ nhân viên",
            value: stats.employee_count,
            icon: <Users size={20} />,
            note: "Trong phạm vi được cấp quyền",
            tone: "teal",
          },
          {
            label: "Trang đã số hóa",
            value: stats.page_count,
            icon: <ScanLine size={20} />,
            note: "Ảnh gốc trong kho private",
            tone: "blue",
          },
          {
            label: "Tài liệu đã xác minh",
            value: verified,
            icon: <FileCheck2 size={20} />,
            note: "Sẵn sàng để tìm kiếm",
            tone: "green",
          },
          {
            label: "Đang chờ kiểm tra",
            value: pending,
            icon: <FileClock size={20} />,
            note: "Cần HR đối chiếu và xác nhận",
            tone: "amber",
          },
        ].map((s) => (
          <article className="stat" key={s.label}>
            <div className="stat-top">
              <span>{s.label}</span>
              <span className={"stat-icon " + s.tone}>{s.icon}</span>
            </div>
            <strong>{s.value.toLocaleString("vi-VN")}</strong>
            <small>{s.note}</small>
          </article>
        ))}
      </section>
      <div className="overview-grid">
        <section className="workflow-card">
          <div>
            <span className="eyebrow">TỪ GIẤY ĐẾN DỮ LIỆU</span>
            <h2>
              Một quy trình.
              <br />
              {" Không còn những file rời rạc."}
            </h2>
            <p>
              Chụp tại nơi lưu hồ sơ. Hệ thống đọc và sắp xếp; HR xác nhận những
              điều quan trọng.
            </p>
            {canCapture && (
              <button className="button white" onClick={onCapture}>
                Bắt đầu số hóa
                <ArrowUpRight size={16} />
              </button>
            )}
          </div>
          <div className="workflow-steps">
            {[
              [ScanLine, "Chụp & gửi", "Ảnh gốc được lưu private"],
              [Sparkles, "Đọc & phân loại", "OCR và trích xuất theo trường"],
              [ClipboardCheck, "HR xác minh", "Đối chiếu từng trang nguồn"],
              [Search, "Tìm & sử dụng", "Tra cứu dữ liệu đã duyệt"],
            ].map(([Icon, title, note], i) => {
              const I = Icon as typeof ScanLine;
              return (
                <div className="workflow-step" key={i}>
                  <span>
                    <I size={18} />
                  </span>
                  <div>
                    <b>{String(title)}</b>
                    <small>{String(note)}</small>
                  </div>
                  <i>{String(i + 1).padStart(2, "0")}</i>
                </div>
              );
            })}
          </div>
        </section>
        <section className="review-prompt">
          <span className="mini-label">
            <span className="live-dot" /> ĐIỂM CẦN CHÚ Ý
          </span>
          <div className="review-prompt-icon">
            <ClipboardCheck size={30} />
          </div>
          <h3>
            {pending > 0
              ? `${pending} tài liệu cần bạn kiểm tra`
              : "Sẵn sàng cho hồ sơ đầu tiên"}
          </h3>
          <p>
            {pending > 0
              ? "Một vài phút đối chiếu để dữ liệu trở nên đáng tin cậy. Tài liệu chưa duyệt sẽ không xuất hiện trong kho tra cứu."
              : "Chọn một nhân viên giả lập và chụp tài liệu. Kết quả đọc tự động sẽ đi vào hàng đợi HR."}
          </p>
          {user.role === "REVIEWER" ? (
            <button className="button secondary full" onClick={onReview}>
              Mở hàng đợi kiểm tra
              <ArrowRight size={16} />
            </button>
          ) : canCapture ? (
            <button className="button secondary full" onClick={onCapture}>
              Tạo phiên scan
              <ArrowRight size={16} />
            </button>
          ) : (
            <div className="notice">
              Bạn đang có quyền xem tài liệu đã xác minh.
            </div>
          )}
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>
              {user.role === "REVIEWER"
                ? "Tài liệu cần kiểm tra"
                : "Tài liệu đã xác minh"}
            </h2>
            <p>Thông tin trong phạm vi hồ sơ được giao cho bạn.</p>
          </div>
          <span className="muted small">{rows.length} tài liệu gần đây</span>
        </div>
        {rows.length ? (
          <Table rows={rows.slice(0, 5)} onOpen={onOpen} />
        ) : (
          <Empty
            title="Hành trình số hóa bắt đầu từ đây"
            detail="Chưa có tài liệu trong danh sách này. Hãy tạo phiên scan để bắt đầu."
          />
        )}
      </section>
      <div className="trust-row">
        <ShieldCheck size={16} /> Kho ảnh private
        <span />
        Đối chiếu nguồn trước khi duyệt
        <span />
        Lịch sử thao tác được lưu lại
      </div>
    </>
  );
}

function Listing({
  review,
  onOpen,
  types,
  notify,
  refresh,
}: {
  review: boolean;
  onOpen: (id: string) => void;
  types: DocType[];
  notify: Notify;
  refresh: number;
}) {
  const [q, setQ] = useState(""),
    [filter, setFilter] = useState(""),
    [rows, setRows] = useState<Row[]>([]),
    [total, setTotal] = useState(0),
    [loading, setLoading] = useState(true),
    [offset, setOffset] = useState(0);
  useEffect(() => {
    setOffset(0);
  }, [q, filter, review]);
  useEffect(() => {
    let ignore = false;
    const timer = window.setTimeout(() => {
      setLoading(true);
      const query = new URLSearchParams({
        q,
        limit: "20",
        offset: String(offset),
      });
      if (filter && !review) query.set("type_code", filter);
      api<{ items: Row[]; total: number }>(
        (review ? "/review-queue" : "/search") + "?" + query,
      )
        .then((r) => {
          if (!ignore) {
            setRows(r.items);
            setTotal(r.total);
          }
        })
        .catch((e) => {
          if (!ignore) notify(errorMessage(e), true);
        })
        .finally(() => {
          if (!ignore) setLoading(false);
        });
    }, 200);
    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [q, filter, review, refresh, offset, notify]);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow text-muted">
            {review ? "HUMAN IN THE LOOP" : "KHO TÀI LIỆU"}
          </div>
          <h1>{review ? "Đối chiếu để tin cậy." : "Tìm đúng điều bạn cần."}</h1>
          <p>
            {review
              ? "Xem ảnh gốc, sửa đề xuất và xác minh trước khi công bố."
              : "Tìm theo nhân viên, loại giấy tờ, giá trị đã xác minh hoặc nội dung OCR."}
          </p>
        </div>
        <span className="count-pill">{total} tài liệu</span>
      </div>
      <section className="panel">
        <div className="filters">
          <label className="search-input">
            <Search size={18} />
            <input
              aria-label="Tìm tài liệu"
              placeholder={
                review
                  ? "Tìm trong hàng đợi kiểm tra…"
                  : "Tên, mã nhân viên hoặc nội dung tài liệu…"
              }
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            {q && (
              <button onClick={() => setQ("")} aria-label="Xóa tìm kiếm">
                <X size={16} />
              </button>
            )}
          </label>
          {!review && (
            <select
              aria-label="Loại tài liệu"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="">Tất cả loại giấy tờ</option>
              {types
                .filter((t) => t.code !== "unknown")
                .map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.name}
                  </option>
                ))}
            </select>
          )}
          <span className="small muted">
            {loading ? "Đang tải…" : `${total} kết quả`}
          </span>
        </div>
        {loading && !rows.length ? (
          <Empty
            title="Đang tải tài liệu…"
            detail="Đang lấy dữ liệu trong phạm vi được cấp quyền."
          />
        ) : rows.length ? (
          <Table rows={rows} onOpen={onOpen} />
        ) : (
          <Empty
            title={
              q
                ? "Chưa tìm thấy tài liệu phù hợp"
                : review
                  ? "Chưa có tài liệu cần kiểm tra"
                  : "Chưa có tài liệu đã xác minh"
            }
            detail={
              q
                ? "Thử mã nhân viên hoặc từ khóa khác. Chỉ tìm trong hồ sơ bạn được cấp quyền."
                : review
                  ? "Tài liệu xử lý xong sẽ xuất hiện ở đây."
                  : "Hồ sơ chưa số hóa hoặc chưa được HR xác minh sẽ chưa xuất hiện trong kho này."
            }
          />
        )}
        <div className="pagination">
          <span className="small muted">
            {review
              ? "Mọi tài liệu đều cần được HR kiểm tra."
              : "Chỉ hiển thị tài liệu đã xác minh. OCR nguồn có thể còn lỗi nhận dạng."}
          </span>
          <div>
            <button
              className="button ghost"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - 20))}
            >
              Trước
            </button>
            <button
              className="button ghost"
              disabled={offset + 20 >= total}
              onClick={() => setOffset(offset + 20)}
            >
              Tiếp
            </button>
          </div>
        </div>
      </section>
    </>
  );
}

function Audit({ refresh, notify }: { refresh: number; notify: Notify }) {
  const [rows, setRows] = useState<
    {
      id: string;
      action: string;
      resource_type: string;
      resource_id: string;
      outcome: string;
      created_at: string;
    }[]
  >([]);
  useEffect(() => {
    api<typeof rows>("/audit")
      .then(setRows)
      .catch((e) => notify(errorMessage(e), true));
  }, [refresh, notify]);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow text-muted">TRUY VẾT</div>
          <h1>Mỗi thao tác đều rõ ràng.</h1>
          <p>
            Nhật ký hoạt động gần đây. Nội dung hồ sơ không được ghi vào nhật ký
            vận hành.
          </p>
        </div>
      </div>
      <section className="panel">
        {rows.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>SỰ KIỆN</th>
                  <th>ĐỐI TƯỢNG</th>
                  <th>KẾT QUẢ</th>
                  <th>THỜI GIAN</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <b className="small">{r.action}</b>
                    </td>
                    <td>
                      <span className="small">{r.resource_type}</span>
                      <small className="mono">
                        {r.resource_id?.slice(0, 8) || "—"}
                      </small>
                    </td>
                    <td>
                      <span
                        className={
                          "status " +
                          (r.outcome === "DENIED"
                            ? "status-rejected"
                            : "status-verified")
                        }
                      >
                        {r.outcome === "ALLOWED"
                          ? "Thành công"
                          : r.outcome === "DENIED"
                            ? "Bị từ chối"
                            : "Thất bại"}
                      </span>
                    </td>
                    <td className="small muted">
                      {new Date(r.created_at).toLocaleString("vi-VN")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="Chưa có hoạt động"
            detail="Các thao tác của bạn sẽ được ghi nhận tại đây."
          />
        )}
      </section>
    </>
  );
}

function App() {
  function landingTab(u: User): Tab {
    return new URLSearchParams(window.location.search).get("scan") === "1" &&
      ["CAPTURE", "REVIEWER"].includes(u.role)
      ? "capture"
      : "overview";
  }
  const [user, setUser] = useState<User | null>(null),
    [boot, setBoot] = useState(true),
    [tab, setTab] = useState<Tab>("overview"),
    [docId, setDocId] = useState<string | null>(null),
    [sidebar, setSidebar] = useState(false);
  const [employees, setEmployees] = useState<Employee[]>([]),
    [types, setTypes] = useState<DocType[]>([]),
    [stats, setStats] = useState<Stats>({
      employee_count: 0,
      page_count: 0,
      documents: {},
      jobs: {},
      demo_mode: false,
    }),
    [recent, setRecent] = useState<Row[]>([]),
    [refresh, setRefresh] = useState(0),
    [toast, setToast] = useState<{ message: string; error: boolean } | null>(
      null,
    );
  const notify = React.useCallback<Notify>((message, error = false) => {
    setToast({ message, error });
  }, []);
  function clearWorkspace() {
    setEmployees([]);
    setTypes([]);
    setRecent([]);
    setDocId(null);
    setSidebar(false);
    setToast(null);
    setStats({
      employee_count: 0,
      page_count: 0,
      documents: {},
      jobs: {},
      demo_mode: false,
    });
  }
  useEffect(() => {
    api<{ user: User; csrf_token: string }>("/auth/me")
      .then((r) => {
        setCsrf(r.csrf_token);
        setUser(r.user);
        setTab(landingTab(r.user));
      })
      .catch(() => {})
      .finally(() => setBoot(false));
    const expire = () => {
      setUser(null);
      setCsrf("");
      clearWorkspace();
    };
    window.addEventListener("docentra:session-expired", expire);
    return () => window.removeEventListener("docentra:session-expired", expire);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 6500);
    return () => window.clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (!user) return;
    let ignore = false;
    Promise.all([
      api<Employee[]>("/employees"),
      api<DocType[]>("/document-types"),
      api<Stats>("/dashboard"),
    ])
      .then(([e, t, s]) => {
        if (ignore) return;
        setEmployees(e);
        setTypes(t);
        setStats(s);
      })
      .catch((e) => {
        if (!ignore) notify(errorMessage(e), true);
      });
    if (["REVIEWER", "VIEWER"].includes(user.role))
      api<{ items: Row[] }>(
        (user.role === "REVIEWER" ? "/review-queue" : "/search") + "?limit=5",
      )
        .then((r) => {
          if (!ignore) setRecent(r.items);
        })
        .catch((e) => {
          if (!ignore) notify(errorMessage(e), true);
        });
    else setRecent([]);
    return () => {
      ignore = true;
    };
  }, [user, refresh, notify]);
  function navigate(next: Tab) {
    setTab(next);
    setDocId(null);
    setSidebar(false);
  }
  function changed() {
    setRefresh((r) => r + 1);
  }
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      clearWorkspace();
      setUser(null);
      setCsrf("");
      setDocId(null);
      setTab("overview");
    } catch (e) {
      notify(errorMessage(e), true);
    }
  }
  if (boot)
    return (
      <div className="boot">
        <Brand />
        <span>Đang mở không gian làm việc…</span>
      </div>
    );
  if (!user)
    return (
      <Login
        onLogin={(u) => {
          setUser(u);
          setTab(landingTab(u));
        }}
      />
    );
  const nav = [
    { id: "overview" as Tab, title: "Tổng quan", icon: LayoutDashboard },
    ...(["CAPTURE", "REVIEWER"].includes(user.role)
      ? [{ id: "capture" as Tab, title: "Số hóa hồ sơ", icon: ScanLine }]
      : []),
    ...(user.role === "REVIEWER"
      ? [
          {
            id: "review" as Tab,
            title: "Kiểm tra & xác minh",
            icon: ClipboardCheck,
          },
        ]
      : []),
    ...(["REVIEWER", "VIEWER"].includes(user.role)
      ? [{ id: "library" as Tab, title: "Kho tài liệu", icon: FolderClosed }]
      : []),
    { id: "audit" as Tab, title: "Lịch sử hoạt động", icon: ShieldCheck },
  ];
  return (
    <div className="shell">
      <aside className={"sidebar " + (sidebar ? "open" : "")}>
        <Brand />
        <div className="workspace">
          <span className="workspace-icon">
            <Users size={18} />
          </span>
          <div>
            Phòng Nhân sự<small>Docentra workspace</small>
          </div>
          <span className="workspace-chevron">⌄</span>
        </div>
        <span className="nav-label">KHÔNG GIAN LÀM VIỆC</span>
        <nav>
          {nav.map(({ id, title, icon: Icon }) => (
            <button
              key={id}
              className={tab === id ? "active" : ""}
              onClick={() => navigate(id)}
            >
              <Icon size={19} />
              <span>{title}</span>
              {id === "review" && (stats.documents.NEEDS_REVIEW || 0) > 0 && (
                <b className="nav-count">{stats.documents.NEEDS_REVIEW}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="storage-note">
            <ShieldCheck size={19} />
            <div>
              Được lưu trữ private<small>Ảnh gốc · Nguồn · Lịch sử</small>
            </div>
          </div>
          <div className="user-box">
            <span className="avatar">{user.full_name.charAt(0)}</span>
            <div>
              <b>{user.full_name}</b>
              <small>
                {user.role === "REVIEWER"
                  ? "HR reviewer"
                  : user.role === "CAPTURE"
                    ? "Người số hóa"
                    : user.role === "ADMIN"
                      ? "Quản trị vận hành"
                      : "Người tra cứu"}
              </small>
            </div>
            <button
              className="icon-button"
              onClick={logout}
              title="Đăng xuất"
              aria-label="Đăng xuất"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      {sidebar && (
        <button
          className="sidebar-backdrop"
          aria-label="Đóng menu"
          onClick={() => setSidebar(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <button
            className="mobile-menu icon-button"
            aria-label="Mở menu"
            onClick={() => setSidebar(true)}
          >
            <Menu size={22} />
          </button>
          <div className="breadcrumb">
            Không gian làm việc
            <ChevronRight size={14} />
            <strong>{nav.find((n) => n.id === tab)?.title}</strong>
          </div>
          <div className="topbar-right">
            <span className="demo-badge">
              <span />
              {stats.demo_mode ? "DỮ LIỆU GIẢ LẬP" : "KHÔNG GIAN NỘI BỘ"}
            </span>
            <button
              className="icon-button"
              aria-label="Mở hàng đợi cần kiểm tra"
              onClick={() =>
                navigate(user.role === "REVIEWER" ? "review" : "audit")
              }
            >
              <Bell size={18} />
            </button>
            <span className="avatar small-avatar">
              {user.full_name.charAt(0)}
            </span>
          </div>
        </header>
        <main className={"content " + (docId ? "detail-content" : "")}>
          {docId ? (
            <DocumentScreen
              id={docId}
              types={types}
              user={user}
              notify={notify}
              onBack={() => setDocId(null)}
              onChanged={changed}
            />
          ) : (
            <>
              {tab === "overview" && (
                <Overview
                  stats={stats}
                  rows={recent}
                  user={user}
                  onCapture={() => navigate("capture")}
                  onReview={() => navigate("review")}
                  onOpen={setDocId}
                />
              )}
              {(tab === "review" || tab === "library") && (
                <Listing
                  key={tab}
                  review={tab === "review"}
                  onOpen={setDocId}
                  types={types}
                  notify={notify}
                  refresh={refresh}
                />
              )}
              {tab === "audit" && <Audit refresh={refresh} notify={notify} />}
            </>
          )}
          {["CAPTURE", "REVIEWER"].includes(user.role) && (
            <div hidden={tab !== "capture" || !!docId}>
              <Capture
                active={tab === "capture" && !docId}
                employees={employees}
                types={types}
                notify={notify}
                onReview={
                  user.role === "REVIEWER"
                    ? () => navigate("review")
                    : undefined
                }
                onDone={() => {
                  changed();
                  notify(
                    user.role === "REVIEWER"
                      ? "Tài liệu đã sẵn sàng để HR kiểm tra."
                      : "Đã gửi tài liệu đến hàng đợi HR.",
                  );
                }}
              />
            </div>
          )}
        </main>
        <footer className="app-footer">
          <span>Docentra · Từ trang giấy đến thông tin rõ ràng.</span>
          <span>
            MVP 0.1 <span className="footer-dot" /> Human-verified by design
          </span>
        </footer>
      </div>
      {toast && (
        <div
          className={"toast " + (toast.error ? "toast-error" : "")}
          role="status"
        >
          {toast.error ? <X size={19} /> : <Check size={19} />}
          <span>{toast.message}</span>
          <button
            className="icon-button"
            onClick={() => setToast(null)}
            aria-label="Đóng thông báo"
          >
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
