import type { AgreementStatus, RenewalStatus, SignedCopyStatus } from "../types";

// Mirrors the Literal types on backend/app/models.py Agreement.
export const AGREEMENT_STATUSES: { id: AgreementStatus; label: string }[] = [
  { id: "draft", label: "Draft" }, { id: "under_review", label: "Under review" }, { id: "active", label: "Active" },
  { id: "expired", label: "Expired" }, { id: "closed", label: "Closed" },
];
export const SIGNED_COPY: { id: SignedCopyStatus; label: string }[] = [
  { id: "received", label: "Received" }, { id: "pending", label: "Pending" }, { id: "unknown", label: "Not confirmed" },
];
export const RENEWAL: { id: RenewalStatus; label: string }[] = [
  { id: "none", label: "Not started" }, { id: "in_progress", label: "Renewal in progress" },
  { id: "renewed", label: "Renewed" }, { id: "not_renewing", label: "Not renewing" },
];
export const labelOf = <T extends string>(options: { id: T; label: string }[], id: T) => options.find((o) => o.id === id)?.label ?? id;

/** Only http(s) links are rendered; anything else (e.g. javascript:) is shown as plain text. */
export function isWebLink(url?: string | null): url is string {
  return Boolean(url && /^https?:\/\//i.test(url.trim()));
}
