import { firebaseAuth } from "../lib/firebase";
import type {
  ActionItem, Activity, Agreement, Alert, AlertReview, AlertsResponse, AnalyzeResponse, DashboardResponse, FinanceRecord, Followup,
  HealthResponse, ImportPreview, Milestone,
  Opportunity, Partner, Project, ReportRecord, SourceDocument, DocumentReview, AmendmentChange,
  ApprovalCheck, ApprovalResult, ProposalCollection, DashboardSummary, AppOptions,
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

/** An HTTP error from the backend; `status` is 0 when the backend could not be reached. */
export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); this.name = "ApiError"; }
}

async function authHeaders(): Promise<Record<string, string>> {
  const user = firebaseAuth?.currentUser;
  if (!user) return {};
  return { Authorization: `Bearer ${await user.getIdToken()}` };
}

function errorMessage(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  // FastAPI request validation returns a list of {loc, msg}.
  if (Array.isArray(detail)) return detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d))).join("; ");
  // Structured 409s: {message, blockers: [...]} or {message, conflicts: [...]}.
  if (detail && typeof detail === "object" && "message" in detail) {
    const d = detail as { message: unknown; blockers?: unknown; conflicts?: unknown };
    const extra = Array.isArray(d.blockers) ? d.blockers.map(String).join(" ")
      : Array.isArray(d.conflicts) ? d.conflicts.map((c) => JSON.stringify(c)).join("; ") : "";
    return extra ? `${String(d.message)}: ${extra}` : String(d.message);
  }
  return `Request failed (${status})`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...(await authHeaders()), ...(init?.headers as Record<string, string> | undefined) };
  // JSON bodies are sent as strings; FormData uploads let the browser set the multipart boundary.
  if (typeof init?.body === "string") headers["Content-Type"] = "application/json";
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(`Cannot reach the ObliGOT API at ${API_BASE}.`, 0);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(errorMessage(body.detail, response.status), response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function requestBlob(path: string): Promise<Blob> {
  const headers = await authHeaders();
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { headers });
  } catch {
    throw new ApiError(`Cannot reach the ObliGOT API at ${API_BASE}.`, 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(errorMessage(body.detail, response.status), response.status);
  }
  return response.blob();
}

function query(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter((entry): entry is [string, string] => Boolean(entry[1]));
  return entries.length ? `?${new URLSearchParams(entries)}` : "";
}

const send = (method: string, payload: unknown): RequestInit => ({ method, body: JSON.stringify(payload) });
const id = (value: string) => encodeURIComponent(value);

/** Standard list/get/create/update/remove for a partner-linked collection. */
function partnerLinked<T>(path: string) {
  return {
    list: (partnerId?: string, params: Record<string, string | undefined> = {}) => request<T[]>(`${path}${query({ partner_id: partnerId, ...params })}`),
    get: (recordId: string) => request<T>(`${path}/${id(recordId)}`),
    create: (payload: Partial<T>) => request<T>(path, send("POST", payload)),
    update: (recordId: string, payload: Partial<T>) => request<T>(`${path}/${id(recordId)}`, send("PATCH", payload)),
    remove: (recordId: string) => request<void>(`${path}/${id(recordId)}`, { method: "DELETE" }),
  };
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  dashboardSummary: () => request<DashboardSummary>("/api/dashboard/summary"),
  options: () => request<AppOptions>("/api/options"),
  dashboard: () => request<DashboardResponse>("/api/dashboard"),
  partners: {
    list: (q?: string) => request<Partner[]>(`/api/partners${query({ q })}`),
    get: (partnerId: string) => request<Partner>(`/api/partners/${id(partnerId)}`),
    create: (payload: Partial<Partner>) => request<Partner>("/api/partners", send("POST", payload)),
    update: (partnerId: string, payload: Partial<Partner>) => request<Partner>(`/api/partners/${id(partnerId)}`, send("PATCH", payload)),
    remove: (partnerId: string) => request<void>(`/api/partners/${id(partnerId)}`, { method: "DELETE" }),
  },
  actions: {
    list: (filters: { status?: string; relatedPartnerId?: string } = {}) =>
      request<ActionItem[]>(`/api/actions${query({ status: filters.status, related_partner_id: filters.relatedPartnerId })}`),
    get: (actionId: string) => request<ActionItem>(`/api/actions/${id(actionId)}`),
    create: (payload: Partial<ActionItem>) => request<ActionItem>("/api/actions", send("POST", payload)),
    update: (actionId: string, payload: Partial<ActionItem>) => request<ActionItem>(`/api/actions/${id(actionId)}`, send("PATCH", payload)),
    remove: (actionId: string) => request<void>(`/api/actions/${id(actionId)}`, { method: "DELETE" }),
  },
  agreements: partnerLinked<Agreement>("/api/agreements"),
  projects: partnerLinked<Project>("/api/projects"),
  finance: partnerLinked<FinanceRecord>("/api/finance"),
  reports: partnerLinked<ReportRecord>("/api/reports"),
  opportunities: partnerLinked<Opportunity>("/api/opportunities"),
  milestones: {
    list: (filters: { projectId?: string; partnerId?: string; status?: string } = {}) =>
      request<Milestone[]>(`/api/milestones${query({ project_id: filters.projectId, partner_id: filters.partnerId, status: filters.status })}`),
    get: (milestoneId: string) => request<Milestone>(`/api/milestones/${id(milestoneId)}`),
    create: (payload: Partial<Milestone>) => request<Milestone>("/api/milestones", send("POST", payload)),
    update: (milestoneId: string, payload: Partial<Milestone>) => request<Milestone>(`/api/milestones/${id(milestoneId)}`, send("PATCH", payload)),
    remove: (milestoneId: string) => request<void>(`/api/milestones/${id(milestoneId)}`, { method: "DELETE" }),
  },
  alerts: {
    list: (filters: { partnerId?: string; level?: string; category?: string; includeReviewed?: boolean } = {}) =>
      request<AlertsResponse>(`/api/alerts${query({ partner_id: filters.partnerId, level: filters.level, category: filters.category, include_reviewed: filters.includeReviewed ? "true" : undefined })}`),
    review: (alertId: string, payload: { decision: "acknowledged" | "deferred" | "dismissed"; deferred_until?: string; reason?: string; note?: string }) =>
      request<Alert & { review: AlertReview }>(`/api/alerts/${id(alertId)}/review`, send("POST", payload)),
    clearReview: (alertId: string) => request<void>(`/api/alerts/${id(alertId)}/review`, { method: "DELETE" }),
    createTask: (alertId: string, payload: { title?: string; owner?: string; due_date?: string | null; priority?: string }) =>
      request<{ task: ActionItem; alert: Alert }>(`/api/alerts/${id(alertId)}/task`, send("POST", payload)),
  },
  activities: {
    list: (filters: { partnerId?: string; entityId?: string; limit?: number } = {}) =>
      request<Activity[]>(`/api/activities${query({ partner_id: filters.partnerId, entity_id: filters.entityId, limit: filters.limit ? String(filters.limit) : undefined })}`),
  },
  followups: {
    list: (filters: { status?: string; relatedPartnerId?: string } = {}) =>
      request<Followup[]>(`/api/followups${query({ status: filters.status, related_partner_id: filters.relatedPartnerId })}`),
    get: (followupId: string) => request<Followup>(`/api/followups/${id(followupId)}`),
    create: (payload: Partial<Followup>) => request<Followup>("/api/followups", send("POST", payload)),
    update: (followupId: string, payload: Pick<Followup, "status">) => request<Followup>(`/api/followups/${id(followupId)}`, send("PATCH", payload)),
    remove: (followupId: string) => request<void>(`/api/followups/${id(followupId)}`, { method: "DELETE" }),
  },
  importPreview: (file: File, entityType: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("entity_type", entityType);
    return request<ImportPreview>("/api/import/preview", { method: "POST", body: form });
  },
  analyze: (payload: { partner_id?: string; context?: string }) => request<AnalyzeResponse>("/api/intelligence/analyze", send("POST", payload)),
  documents: {
    list: (filters: { partnerId?: string; agreementId?: string; status?: string; kind?: string } = {}) =>
      request<SourceDocument[]>(`/api/documents${query({ partner_id: filters.partnerId, agreement_id: filters.agreementId, status: filters.status, kind: filters.kind })}`),
    get: (documentId: string) => request<SourceDocument>(`/api/documents/${id(documentId)}`),
    upload: (file: File, kind: "mou" | "addendum", partnerId?: string, agreementId?: string) => {
      const form = new FormData(); form.append("file", file); form.append("kind", kind);
      if (partnerId) form.append("partner_id", partnerId); if (agreementId) form.append("agreement_id", agreementId);
      return request<SourceDocument>("/api/documents", { method: "POST", body: form });
    },
    /** Start reading/extraction in the background; poll `get` for status and progress. */
    extract: (documentId: string) => request<SourceDocument>(`/api/documents/${id(documentId)}/extract`, { method: "POST" }),
    /** Proposals and issues for review (GET /extraction), in the review screen's shape. */
    review: async (documentId: string): Promise<DocumentReview> => {
      const r = await request<Omit<DocumentReview, "fields" | "issues"> & { extracted_fields: DocumentReview["fields"]; review_issues: DocumentReview["issues"] }>(
        `/api/documents/${id(documentId)}/extraction`);
      return { document: r.document, fields: r.extracted_fields, clauses: r.clauses, financial_terms: r.financial_terms,
        obligations: r.obligations, programme_scope: r.programme_scope, tables: r.tables ?? [], issues: r.review_issues };
    },
    decide: (documentId: string, collection: ProposalCollection, itemId: string,
      payload: { decision: "approve" | "reject" | "defer" | "reset"; value?: string | number | boolean | null; note?: string }) =>
      request<Record<string, unknown>>(`/api/documents/${id(documentId)}/proposals/${collection}/${id(itemId)}`, send("PATCH", payload)),
    resolveIssue: (documentId: string, issueId: string, payload: { status: "resolved" | "deferred" | "open"; resolution?: string }) =>
      request<Record<string, unknown>>(`/api/documents/${id(documentId)}/issues/${id(issueId)}`, send("PATCH", payload)),
    approvalCheck: (documentId: string, options: { partnerId?: string; createPartner?: boolean } = {}) =>
      request<ApprovalCheck>(`/api/documents/${id(documentId)}/approval-check${query({ partner_id: options.partnerId, create_partner: options.createPartner ? "true" : undefined })}`),
    approve: (documentId: string, options: { partner_id?: string; create_partner?: boolean; owner?: string } = {}) =>
      request<ApprovalResult>(`/api/documents/${id(documentId)}/approve`, send("POST", options)),
    /** One page as a JPEG (authenticated), for comparing extracted values with the source. */
    pageImage: (documentId: string, page: number) => requestBlob(`/api/documents/${id(documentId)}/pages/${page}/image`),
    history: (agreementId: string) =>
      request<{ changes: AmendmentChange[]; original: Record<string, unknown>; effective: Record<string, unknown> }>(`/api/agreements/${id(agreementId)}/history`),
    decideAmendment: (changeId: string, decision: "approve" | "reject" | "unresolved" | "reset", extra: { effective_date?: string; note?: string } = {}) =>
      request<AmendmentChange>(`/api/agreement-changes/${id(changeId)}`, send("PATCH", { decision, ...extra })),
    exportWorkbook: () => requestBlob("/api/export/workbook"),
  },
};
