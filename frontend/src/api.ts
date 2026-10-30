let csrfToken = "";
export function setCsrf(value: string) {
  csrfToken = value;
}
export function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Không thể hoàn tất thao tác.";
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (options.method && !["GET", "HEAD"].includes(options.method))
    headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch("/api/v1" + path, {
    ...options,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login")
      window.dispatchEvent(new Event("docentra:session-expired"));
    throw new Error(
      body.error?.message || "Không thể hoàn tất thao tác. Vui lòng thử lại.",
    );
  }
  return body as T;
}
