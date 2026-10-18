// Mirrors the Pydantic models in backend/app/models.py. Keep both in sync.
export type PartnerStatus = "prospect" | "qualification" | "active" | "on_hold" | "closed";
export type Priority = "high" | "medium" | "low";
export type ActionStatus = "open" | "in_review" | "done" | "deferred";
export type RecordStatus = "planned" | "active" | "on_hold" | "completed" | "closed";
export type MilestoneStatus = "planned" | "in_progress" | "completed" | "missed" | "cancelled";
export type AgreementStatus = "draft" | "under_review" | "active" | "expired" | "closed";
export type SignedCopyStatus = "received" | "pending" | "unknown";
export type RenewalStatus = "none" | "in_progress" | "renewed" | "not_renewing";
export type FinanceType = "budget" | "fund_received" | "invoice" | "utilization_certificate";
export type ReportType = "monthly" | "quarterly" | "impact" | "other";
export type ReportStatus = "planned" | "due" | "submitted" | "overdue" | "accepted";
export type SourceLabel = "demo" | "user" | string;
export type OpportunityStage = "identified" | "qualification" | "proposal" | "approval" | "agreement" | "active" | "renewal" | "closed";

export interface Partner {
  id: string; name: string; category: string; contribution_types?: string[]; status: PartnerStatus;
  owner: string; updated_at: string; summary: string; contact_name?: string | null;
  contact_email?: string | null; source_label?: SourceLabel;
}
export interface ActionItem {
  id: string; title: string; priority: Priority; status: ActionStatus; due_date?: string | null;
  evidence: string[]; recommended_action: string; owner?: string; related_partner_id?: string | null;
  source_alert_id?: string | null; source_label?: SourceLabel;
}
export interface Agreement {
  id: string; partner_id: string; title: string; reference_number?: string | null; status: AgreementStatus;
  start_date?: string | null; expiry_date?: string | null; owner: string; document_url?: string | null;
  signed_copy: SignedCopyStatus; renewal_status: RenewalStatus; project_id?: string | null; opportunity_id?: string | null;
  source_label?: SourceLabel;
}
export interface Project {
  id: string; partner_id?: string | null; name: string; status: RecordStatus; owner: string;
  start_date?: string | null; end_date?: string | null; milestone_summary: string; source_label?: SourceLabel;
}
export interface Milestone {
  id: string; project_id: string; partner_id?: string | null; title: string; due_date?: string | null;
  completed_date?: string | null; status: MilestoneStatus; owner: string; source_label?: SourceLabel;
}
export interface FinanceRecord {
  id: string; partner_id: string; project_id?: string | null; record_type: FinanceType; title: string;
  amount?: number | null; currency: string; issue_date?: string | null; due_date?: string | null;
  received_date?: string | null; status: string;
  reference_number?: string | null; financial_term_id?: string | null; source_label?: SourceLabel;
}
export interface ReportRecord {
  id: string; partner_id: string; project_id?: string | null; title: string; report_type: ReportType;
  due_date?: string | null; submitted_date?: string | null; status: ReportStatus; owner: string;
  source_label?: SourceLabel;
}
export interface Opportunity {
  id: string; partner_id: string; title: string; stage: OpportunityStage; owner: string;
  next_step: string; next_step_date?: string | null; updated_at: string; source_label?: SourceLabel;
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
export type DocumentKind = "mou" | "addendum";
export type DocumentStatus = "uploaded" | "extracting" | "extracted" | "needs_review" | "approved" | "failed" | "blocked" | "retry_required";
// Documents and extraction output (backend/app/documents.py and document_routes.py).
export interface ExtractionRun {
  started_at: string; finished_at?: string | null; model: string; pages_to_read: number; pages_read: number;
  chunks_total: number; chunks_done: number; pages_sent: number[]; pages_skipped_low_text: number[];
  ai_used: boolean; ai_error?: string | null; counts: Record<string, number>;
  /** groq: fully AI-extracted; partial: Groq for some parts, pattern matching for the rest; deterministic: no AI extraction. */
  mode: "groq" | "gemini" | "partial" | "deterministic"; retryable: boolean; note?: string | null;
}
export interface SourceDocument {
  id: string; filename: string; kind: DocumentKind; partner_id?: string | null; agreement_id?: string | null;
  uploaded_at: string; uploaded_by: string; page_count?: number | null; status: DocumentStatus;
  pages?: { page_number: number; char_count: number; text_status: "text" | "low_text" }[];
  warnings: string[]; error?: string | null; extraction?: ExtractionRun | null;
  approved_by?: string | null; approved_at?: string | null; source_label?: SourceLabel;
  archived?: boolean; archived_at?: string | null; archived_by?: string | null; archived_reason?: string | null;
}
export type ProposalReviewState = "proposed" | "needs_review" | "approved" | "rejected" | "deferred";
export interface DocumentEvidence {
  document_id: string; page: number; quote: string; verified: boolean; verification_error?: string | null;
  /** text_layer: matched the PDF's own text; ai_transcript: matched an AI transcription of a scanned page (weaker). */
  basis?: "text_layer" | "ai_transcript" | "ocr_text" | null; section?: string | null; printed_page?: string | null;
}
interface ProposalBase {
  id: string; document_id: string; review_state: ProposalReviewState; warnings: string[];
  evidence?: DocumentEvidence | null; reviewed_by?: string | null; reviewed_at?: string | null;
}
type Scalar = string | number | boolean | null;
export interface ExtractedField extends ProposalBase {
  target: string; field: string; verbatim?: string | null; proposed_value?: Scalar; approved_value?: Scalar; review_note?: string | null;
}
export interface ClauseProposal extends ProposalBase { clause_type: string; heading?: string | null; summary: string; verbatim: string; needs_legal_review: boolean }
export interface FinancialTermProposal extends ProposalBase {
  term_type: string; description: string; amount?: number | null; currency?: string | null; basis: string;
  financial_year?: string | null; payer?: string | null; due_date?: string | null; condition?: string | null;
}
export interface DeadlineRule {
  deadline_type: "fixed_date" | "relative" | "recurring" | "unspecified"; text?: string | null; offset_value?: number | null;
  offset_unit?: string | null; trigger?: string | null; trigger_event?: string | null; recurrence?: string | null;
}
export interface ObligationProposal extends ProposalBase {
  obligation_type: string; title: string; frequency: string; due_date?: string | null; deadline?: DeadlineRule | null;
  operational_ref?: { collection: string; id: string } | null;
}
export interface ScopeProposal extends ProposalBase {
  dimension: string; value: string; target_value?: number | null; target_unit?: string | null; location?: string | null; period?: string | null;
}
export interface TableProposal extends ProposalBase {
  title: string; kind: string; section?: string | null; pages: number[]; headers: string[];
  rows: { row_index: number; page: number; cells: (string | null)[]; verified: boolean }[];
  currency?: string | null; unit_notes: string[]; notes: string[]; continues_across_pages: boolean;
}
export interface DocumentIssue {
  id: string; document_id: string; severity: "error" | "warning" | "info"; code: string; message: string;
  related_id?: string | null; field?: string | null; page?: number | null; blocks_approval?: boolean; status: "open" | "resolved" | "deferred"; resolution?: string | null;
}
export type ProposalCollection = "extracted_fields" | "clauses" | "financial_terms" | "obligations" | "programme_scope" | "tables";
export interface DocumentReview {
  document: SourceDocument; fields: ExtractedField[]; clauses: ClauseProposal[]; financial_terms: FinancialTermProposal[];
  obligations: ObligationProposal[]; programme_scope: ScopeProposal[]; tables: TableProposal[]; issues: DocumentIssue[];
}
/** An addendum's change to an agreement (GET /api/agreements/{id}/history). */
export interface AmendmentChange {
  id: string; agreement_id: string; addendum_document_id: string; kind: "modify" | "add"; target: string; field: string;
  prior_value?: Scalar; proposed_value?: Scalar; amendment_date?: string | null; effective_date?: string | null;
  evidence: DocumentEvidence; status: "proposed" | "approved" | "rejected" | "unresolved"; note?: string | null;
  reviewed_by?: string | null; applied_at?: string | null;
}
// Rules engine alerts (GET /api/alerts). Mirrors backend/app/engine.py and app/reviews.py.
export type AlertSeverity = "overdue" | "risk" | "due_soon" | "missing_data";
export type AlertCategory = "agreements" | "pipeline" | "projects" | "reporting" | "finance" | "tasks" | "data_quality";
export interface AlertEvidence { label: string; value: string | number; source: "record" | "computed" }
/** kind: urgency (how soon/late), impact (what is at stake), context (other alerts, adjustments). */
export interface PriorityFactor { label: string; points: number; kind?: "urgency" | "impact" | "context" }
export type ReviewDecision = "acknowledged" | "deferred" | "dismissed" | "task_created";
export interface AlertReview {
  id: string; decision: ReviewDecision; deferred_until?: string | null; reason?: string | null; note?: string | null;
  reviewer: string; reviewed_at: string; task_id?: string | null; stale_reason?: string;
}
export interface Alert {
  id: string; rule_id: string; rule_title: string; rule_description: string; category: AlertCategory; severity: AlertSeverity;
  record_type: string; record_id: string; record_title: string; partner_id?: string | null; project_id?: string | null;
  owner: string; due_date?: string | null; days_remaining?: number | null; evidence: AlertEvidence[];
  why_it_matters: string; recommended_action: string; source_label?: SourceLabel; related_alert_ids: string[];
  priority: { score: number; level: Priority; factors: PriorityFactor[]; urgency?: number; impact?: number };
  review: AlertReview | null; previous_review?: AlertReview; hidden_by_review: boolean;
}
export interface AlertsResponse {
  as_of: string; config: Record<string, number>; note: string; alerts: Alert[];
  counts: { total: number; by_level: Record<Priority, number>; hidden_by_review: number };
}
export interface Activity {
  id: string; at: string; actor: string; event: string; summary: string; entity_type: string; entity_id: string;
  partner_id?: string | null; details: Record<string, unknown>;
}
/** POST /api/import/preview (preview only; nothing is written). */
export interface ImportCleanedRow { row: number; data: Record<string, unknown>; warnings: string[]; errors: string[] }
export interface ImportCommitResult {
  entity_type: string; dry_run: boolean; committed: boolean; header_row: number; headers: string[];
  mapping: Record<string, string>; unmapped: string[]; cleaned: ImportCleanedRow[]; rejected: ImportCleanedRow[];
  skipped: { row: number; reason: string }[]; valid_count: number; created: number; new_partners: string[];
}
export interface ImportPreview {
  entity_type: string; filename?: string | null; headers: string[]; preview_rows: Record<string, unknown>[];
  rows_previewed: number; total_rows_detected: number; valid_count: number; invalid_count: number;
  valid_rows: { row: number; name: string | null }[]; issues: { row: number; name: string | null; issues: string[] }[];
  committed: false; warning: string;
}
export interface HealthResponse {
  status: string; app: string; ai_configured: boolean; database?: string; auth_required?: boolean;
}
export interface AnalyzeResponse {
  summary: string; observations: string[]; recommendations: string[]; ai_used: boolean; ai_error?: string | null;
}

// Backend-computed management summary (GET /api/dashboard/summary) and options (GET /api/options).
export interface CurrencyAmount { currency: string; amount: number; count: number }
export interface DashboardSummary {
  as_of: string;
  alerts: { open: number; by_level: Record<"high" | "medium" | "low", number>; by_category: Record<string, number>; overdue: number; mous_expiring_30d: number };
  tasks: { open: number; open_from_alerts: number };
  partners: { total: number; active: number };
  agreements: { active: number; expired: number };
  documents: { awaiting_review: number; needs_attention: number; addenda_awaiting_review: number };
  reporting: { overdue: number; open_reports: number; pending_ucs: number };
  finance: { unpaid_invoices: CurrencyAmount[]; fund_releases_due: CurrencyAmount[]; fund_releases_overdue: CurrencyAmount[] };
  coverage: Record<"state" | "region" | "course" | "location", { label: string; count: number }[]>;
}
export interface AppOptions {
  enums: {
    partner_status: string[]; agreement_status: string[]; signed_copy: string[]; renewal_status: string[]; project_status: string[];
    milestone_status: string[]; opportunity_stage: string[]; finance_record_type: string[]; finance_status: Record<string, string[]>;
    document_kind: string[]; scope_dimension: string[]; import_entity_type: string[]; report_type: string[]; report_status: string[];
    alert_category: string[]; alert_severity: string[]; review_decision: string[];
  };
  /** Display labels per enum group, from the backend. */
  labels: Record<"partner_status" | "agreement_status" | "signed_copy" | "renewal_status" | "project_status" | "milestone_status" |
    "opportunity_stage" | "finance_record_type" | "document_kind" | "report_type" | "report_status" | "alert_category" |
    "alert_severity" | "review_decision", Record<string, string>>;
  partners: { id: string; name: string }[];
  projects: { id: string; name: string; partner_id?: string | null }[];
  agreements: { id: string; title: string; partner_id?: string | null }[];
  states: string[]; programmes: string[];
}
