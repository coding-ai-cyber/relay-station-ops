export type ApiError = {
  detail?: string;
};

const TOKEN_KEY = "sub2api_ops_token";

type ApiRequestOptions = RequestInit & {
  timeoutMs?: number;
};

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 15_000);
  const { timeoutMs, ...fetchOptions } = options;
  void timeoutMs;

  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json; charset=utf-8");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(path, {
      ...fetchOptions,
      headers,
      signal: fetchOptions.signal ?? controller.signal
    });
  } finally {
    window.clearTimeout(timeoutId);
  }

  if (response.status === 401) {
    clearToken();
  }

  if (!response.ok) {
    let message = `请求失败：${response.status}`;
    try {
      const payload = (await response.json()) as ApiError;
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the status-based fallback.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function toQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}
