import { LoginRequest, LoginResponse } from "@/types";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

function toWebSocketBase(httpBaseUrl: string): string {
  try {
    const url = new URL(httpBaseUrl);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url.toString().replace(/\/$/, "");
  } catch {
    return httpBaseUrl.replace(/^https?:/, (m) => (m === "https:" ? "wss:" : "ws:")).replace(/\/$/, "");
  }
}

const WS_BASE_URL = toWebSocketBase(BASE_URL);

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await fetch(`${BASE_URL}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    if (response.status === 401) {
      const data = await response.json();
      throw new Error(data.detail || "Invalid username or password");
    }
    throw new Error("An error occurred. Please try again.");
  }

  return response.json();
}

export function getToken(): string | null {
  return localStorage.getItem("access_token");
}

export function setToken(token: string): void {
  localStorage.setItem("access_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("access_token");
}

export function getWebSocketUrl(): string {
  const token = getToken();
  return `${WS_BASE_URL}/ws/live?token=${encodeURIComponent(token || "")}`;
}

// ---------------------------------------------------------------------------
// History API
// ---------------------------------------------------------------------------
export async function getHistoryDates(): Promise<{ dates: string[]; count: number }> {
  const token = getToken();
  const response = await fetch(`${BASE_URL}/api/history/dates`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Failed to fetch history dates");
  return response.json();
}

export async function downloadHistoryCSV(dateStr: string): Promise<void> {
  const token = getToken();
  const response = await fetch(
    `${BASE_URL}/api/history/download?date_str=${encodeURIComponent(dateStr)}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Download failed" }));
    throw new Error(err.detail || "Download failed");
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `preopen_snapshot_${dateStr}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function saveSnapshotNow(): Promise<{ status: string; date: string }> {
  const token = getToken();
  const response = await fetch(`${BASE_URL}/api/history/save-now`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Failed to save snapshot");
  return response.json();
}
