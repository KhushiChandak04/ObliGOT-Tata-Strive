import { onAuthStateChanged } from "firebase/auth";
import { firebaseAuth } from "../lib/firebase";
import type { ActionItem, HealthResponse, Partner } from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function authHeaders(): Promise<Record<string, string>> {
  const user = firebaseAuth?.currentUser;
  if (!user) return {};
  return { Authorization: `Bearer ${await user.getIdToken()}` };
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = { "Content-Type": "application/json", ...(await authHeaders()), ...(init?.headers || {}) };
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export const api = {
  health: () => request<HealthResponse>("/api/health"),
  dashboard: () => request<Record<string, unknown>>("/api/dashboard"),
  partners: (q = "") => request<Partner[]>(`/api/partners${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  partner: (id: string) => request<Partner>(`/api/partners/${encodeURIComponent(id)}`),
  createPartner: (payload: Partial<Partner>) => request<Partner>("/api/partners", { method: "POST", body: JSON.stringify(payload) }),
  updatePartner: (id: string, payload: Partial<Partner>) => request<Partner>(`/api/partners/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deletePartner: (id: string) => request<void>(`/api/partners/${encodeURIComponent(id)}`, { method: "DELETE" }),
  actions: () => request<ActionItem[]>("/api/actions"),
  updateAction: (id: string, payload: Partial<ActionItem>) => request<ActionItem>(`/api/actions/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  analyze: (payload: { partner_id?: string; context?: string }) => request<{ summary: string; observations: string[]; recommendations: string[]; ai_used: boolean; ai_error?: string | null }>("/api/intelligence/analyze", { method: "POST", body: JSON.stringify(payload) }),
};
