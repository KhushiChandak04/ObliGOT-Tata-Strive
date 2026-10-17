export type PartnerStatus = "prospect" | "qualification" | "active" | "on_hold" | "closed";
export interface Partner {
  id: string; name: string; category: string; contribution_types?: string[]; status: PartnerStatus;
  owner: string; updated_at: string; summary: string; contact_name?: string | null;
  contact_email?: string | null; source_label?: string;
}
export interface ActionItem {
  id: string; title: string; priority: "high" | "medium" | "low";
  status: "open" | "in_review" | "done" | "deferred"; due_date?: string | null;
  evidence: string[]; recommended_action: string; owner?: string; related_partner_id?: string;
}
export interface HealthResponse {
  status: string; app: string; ai_configured: boolean; database?: string; auth_required?: boolean;
}
