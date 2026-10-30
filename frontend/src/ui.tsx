const labels: Record<string, string> = {
  VERIFIED: "Đã xác minh",
  NEEDS_REVIEW: "Chờ kiểm tra",
  DRAFT: "Đang xử lý",
  REJECTED: "Đã từ chối",
};
export function Status({ value }: { value: string }) {
  return (
    <span className={"status status-" + value.toLowerCase()}>
      <span />
      {labels[value] || value}
    </span>
  );
}
