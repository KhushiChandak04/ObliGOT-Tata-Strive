import { useState, type FormEvent } from "react";
import FormField from "../../components/ui/FormField";
import { api } from "../../services/functions.service";
import { isWebLink } from "../../lib/agreements";
import { EnumOptions } from "../../lib/options";
import type { Agreement, AgreementStatus, Opportunity, Partner, Project, RenewalStatus, SignedCopyStatus } from "../../types";

type FormState = {
  partner_id: string; title: string; reference_number: string; status: AgreementStatus; start_date: string; expiry_date: string;
  owner: string; signed_copy: SignedCopyStatus; renewal_status: RenewalStatus; document_url: string; project_id: string; opportunity_id: string;
};
type Errors = Partial<Record<keyof FormState, string>>;

function validate(form: FormState): Errors {
  const errors: Errors = {};
  if (!form.partner_id) errors.partner_id = "Choose the partner this agreement is with.";
  if (form.title.trim().length < 2) errors.title = "Enter at least 2 characters.";
  if (form.start_date && form.expiry_date && form.expiry_date < form.start_date) errors.expiry_date = "Expiry date must be on or after the start date.";
  if (form.document_url.trim() && !isWebLink(form.document_url)) errors.document_url = "Use a link starting with https:// or http://";
  return errors;
}

/** Create or edit an agreement/MOU. Links to projects and opportunities are limited to the chosen partner. */
export default function AgreementForm({ agreement, partners, projects, opportunities, defaultPartnerId, onSaved, onDeleted, onCancel }: {
  agreement?: Agreement; partners: Partner[]; projects: Project[]; opportunities: Opportunity[]; defaultPartnerId?: string;
  onSaved: (saved: Agreement) => void; onDeleted?: () => void; onCancel: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => ({
    partner_id: agreement?.partner_id ?? defaultPartnerId ?? "", title: agreement?.title ?? "",
    reference_number: agreement?.reference_number ?? "", status: agreement?.status ?? "draft",
    start_date: agreement?.start_date ?? "", expiry_date: agreement?.expiry_date ?? "", owner: agreement?.owner ?? "",
    signed_copy: agreement?.signed_copy ?? "unknown", renewal_status: agreement?.renewal_status ?? "none",
    document_url: agreement?.document_url ?? "", project_id: agreement?.project_id ?? "", opportunity_id: agreement?.opportunity_id ?? "",
  }));
  const [errors, setErrors] = useState<Errors>({});
  const [submitError, setSubmitError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const set = (field: keyof FormState) => (value: string) => {
    setForm((current) => {
      const next = { ...current, [field]: value };
      // Links must stay within one partner, so changing the partner clears them.
      if (field === "partner_id" && value !== current.partner_id) { next.project_id = ""; next.opportunity_id = ""; }
      return next;
    });
    setErrors((current) => (current[field] ? { ...current, [field]: undefined } : current));
  };
  const partnerProjects = projects.filter((p) => p.partner_id === form.partner_id);
  const partnerOpportunities = opportunities.filter((o) => o.partner_id === form.partner_id);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    const blankToNull = (value: string) => value.trim() || null;
    const payload = {
      partner_id: form.partner_id, title: form.title.trim(), reference_number: blankToNull(form.reference_number), status: form.status,
      start_date: form.start_date || null, expiry_date: form.expiry_date || null, owner: form.owner.trim() || "Unassigned",
      signed_copy: form.signed_copy, renewal_status: form.renewal_status, document_url: blankToNull(form.document_url),
      project_id: form.project_id || null, opportunity_id: form.opportunity_id || null,
    };
    setBusy(true); setSubmitError("");
    try { onSaved(agreement ? await api.agreements.update(agreement.id, payload) : await api.agreements.create(payload)); }
    catch (err) { setSubmitError(err instanceof Error ? err.message : "Could not save the agreement."); }
    finally { setBusy(false); }
  }

  async function remove() {
    if (!agreement) return;
    setBusy(true); setSubmitError("");
    try { await api.agreements.remove(agreement.id); onDeleted?.(); }
    catch (err) { setSubmitError(err instanceof Error ? err.message : "Could not delete the agreement."); }
    finally { setBusy(false); }
  }

  const field = (name: keyof FormState, label: string, input: JSX.Element, hint?: string) => (
    <FormField id={`agr-${name}`} label={label} error={errors[name]} hint={hint}>{input}</FormField>
  );

  return <form className="form-grid" onSubmit={(e) => void submit(e)} noValidate>
    {field("partner_id", "Partner *", <select value={form.partner_id} onChange={(e) => set("partner_id")(e.target.value)} disabled={Boolean(defaultPartnerId) && !agreement}><option value="">Select a partner…</option>{partners.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>)}
    {field("title", "Agreement title *", <input value={form.title} onChange={(e) => set("title")(e.target.value)} maxLength={200} autoFocus />)}
    {field("reference_number", "Reference number", <input value={form.reference_number} onChange={(e) => set("reference_number")(e.target.value)} maxLength={100} />)}
    {field("status", "Status", <select value={form.status} onChange={(e) => set("status")(e.target.value)}><EnumOptions group="agreement_status" current={form.status} /></select>, "Record “Active” only for a signed, effective agreement.")}
    {field("start_date", "Start date", <input type="date" value={form.start_date} onChange={(e) => set("start_date")(e.target.value)} />)}
    {field("expiry_date", "Expiry date", <input type="date" value={form.expiry_date} onChange={(e) => set("expiry_date")(e.target.value)} />)}
    {field("signed_copy", "Signed copy", <select value={form.signed_copy} onChange={(e) => set("signed_copy")(e.target.value)}><EnumOptions group="signed_copy" current={form.signed_copy} /></select>)}
    {field("renewal_status", "Renewal", <select value={form.renewal_status} onChange={(e) => set("renewal_status")(e.target.value)}><EnumOptions group="renewal_status" current={form.renewal_status} /></select>)}
    {field("owner", "Responsible owner", <input value={form.owner} onChange={(e) => set("owner")(e.target.value)} maxLength={120} placeholder="Unassigned" />)}
    {field("project_id", "Linked project", <select value={form.project_id} onChange={(e) => set("project_id")(e.target.value)} disabled={!form.partner_id}><option value="">None</option>{partnerProjects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>, form.partner_id && !partnerProjects.length ? "This partner has no projects." : undefined)}
    <div className="form-wide">{field("opportunity_id", "Originating opportunity", <select value={form.opportunity_id} onChange={(e) => set("opportunity_id")(e.target.value)} disabled={!form.partner_id}><option value="">None</option>{partnerOpportunities.map((o) => <option key={o.id} value={o.id}>{o.title}</option>)}</select>)}</div>
    <div className="form-wide">{field("document_url", "Document link", <input type="url" value={form.document_url} onChange={(e) => set("document_url")(e.target.value)} maxLength={2000} placeholder="https://…" />, "Link to the signed copy or draft in your document store.")}</div>
    {submitError && <p className="form-wide form-error" role="alert">{submitError}</p>}
    <div className="form-wide form-actions form-actions-split">
      {agreement && onDeleted ? (confirmingDelete
        ? <span className="inline-confirm">Delete this agreement? <button type="button" className="button button-danger" onClick={() => void remove()} disabled={busy}>Confirm delete</button><button type="button" className="text-button" onClick={() => setConfirmingDelete(false)} disabled={busy}>Keep</button></span>
        : <button type="button" className="text-button danger-text" onClick={() => setConfirmingDelete(true)} disabled={busy}>Delete agreement</button>) : <span />}
      <span className="form-actions">
        <button type="button" className="button button-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
        <button type="submit" className="button button-primary" disabled={busy}>{busy ? "Saving…" : agreement ? "Save changes" : "Create agreement"}</button>
      </span>
    </div>
  </form>;
}
