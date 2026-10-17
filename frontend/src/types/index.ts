// Mirrors the Pydantic models in backend/app/models.py. Keep both in sync.
export type PartnerStatus = "prospect" | "qualification" | "active" | "on_hold" | "closed";
export type Priority = "high" | "medium" | "low";
export type ActionStatus = "open" | "in_review" | "done" | "deferred";
export type RecordStatus = "planned" | "active" | "on_hold" | "completed" | "closed";
export type AgreementStatus = "draft" | "under_review" | "active" | "expired" | "closed";
export type FinanceType = "budget" | "fund_received" | "invoice" | "utilization_certificate";
export type ReportType = "monthly" | "quarterly" | "impact" | "other";
export type ReportStatus = "planned" | "due" | "submitted" | "overdue" | "accepted";
export type SourceLabel = "demo" | "user" | string;

export interface Partner {
  id: string; name: string; category: string; contribution_types?: string[]; status: PartnerStatus;
  owner: string; updated_at: string; summary: string; contact_name?: string | null;
  contact_email?: string | null; source_label?: SourceLabel;
}
export interface ActionItem {
  id: string; title: string; priority: Priority; status: ActionStatus; due_date?: string | null;
  evidence: string[]; recommended_action: string; owner?: string; related_partner_id?: string | null;
  source_label?: SourceLabel;
}
export interface Agreement {
  id: string; partner_id: string; title: string; reference_number?: string | null; status: AgreementStatus;
  start_date?: string | null; expiry_date?: string | null; owner: string; document_url?: string | null;
  source_label?: SourceLabel;
}
export interface Project {
  id: string; partner_id?: string | null; name: string; status: RecordStatus; owner: string;
  start_date?: string | null; end_date?: string | null; milestone_summary: string; source_label?: SourceLabel;
}
export interface FinanceRecord {
  id: string; partner_id: string; project_id?: string | null; record_type: FinanceType; title: string;
  amount?: number | null; currency: string; due_date?: string | null; status: string;
  reference_number?: string | null; source_label?: SourceLabel;
}
export interface ReportRecord {
  id: string; partner_id: string; project_id?: string | null; title: string; report_type: ReportType;
  due_date?: string | null; submitted_date?: string | null; status: ReportStatus; owner: string;
  source_label?: SourceLabel;
}
export interface Followup {
  id: string; title: string; owner: string; due_date?: string | null; related_partner_id?: string | null;
  status: ActionStatus; source_label?: SourceLabel;
}

export interface DeadlineFinding {
  id: string; record_id: string; record_type: string; issue: string; priority: Priority;
  due_date?: string; days_remaining?: number; evidence: string[]; recommended_action: string;
  partner_id?: string | null;
}
export interface DashboardResponse {
  metrics: {
    partners_total: number; partners_active: number; actions_open: number; agreements_active: number;
    projects_active: number; reports_pending: number; finance_records: number;
  };
  findings: DeadlineFinding[];
  as_of: string;
  storage_mode: "firestore" | "demo-memory-fallback";
  demo_data_notice: string;
}
export interface HealthResponse {
  status: string; app: string; ai_configured: boolean; database?: string; auth_required?: boolean;
}
export interface AnalyzeResponse {
  summary: string; observations: string[]; recommendations: string[]; ai_used: boolean; ai_error?: string | null;
}
