// Thin fetch wrapper for the Django API: token header, JSON in/out, file downloads and one error shape.
const TOKEN_KEY = "tms.token";

export const session = {
  get() {
    try {
      return JSON.parse(localStorage.getItem(TOKEN_KEY) || "null");
    } catch {
      return null;
    }
  },
  set(value) {
    try {
      if (value) localStorage.setItem(TOKEN_KEY, JSON.stringify(value));
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable */
    }
  },
};

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export async function api(path, { method = "GET", body, query, blob = false } = {}) {
  const params = query
    ? "?" + new URLSearchParams(Object.entries(query).filter(([, v]) => v !== "" && v != null)).toString()
    : "";
  const headers = { Accept: blob ? "*/*" : "application/json" };
  const token = session.get()?.token;
  if (token) headers.Authorization = `Token ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`/api/${path}${params}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (response.status === 401) {
    session.set(null);
    window.dispatchEvent(new Event("tms:signed-out"));
    throw new ApiError("Your session has ended. Please sign in again.", 401);
  }
  if (response.status === 204) return null;
  if (blob && response.ok) return response.blob();
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(data.error || `Request failed (${response.status})`, response.status, data);
  return data;
}

export function download(blobData, filename) {
  const url = URL.createObjectURL(blobData);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
