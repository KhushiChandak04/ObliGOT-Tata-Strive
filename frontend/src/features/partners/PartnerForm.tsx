import { useState, type FormEvent } from "react";
import { api } from "../../services/functions.service";
import type { Partner, PartnerStatus } from "../../types";

const STATUSES: PartnerStatus[] = ["prospect", "qualification", "active", "on_hold", "closed"];
const STATUS_LABELS: Record<PartnerStatus, string> = { prospect: "Prospect", qualification: "Qualification", active: "Active", on_hold: "On hold", closed: "Closed" };

type FormState = { name: string; category: string; status: PartnerStatus; owner: string; contact_name: string; contact_email: string; summary: string };

function initialState(partner?: Partner): FormState {
  return {
    name: partner?.name ?? "", category: partner?.category ?? "", status: partner?.status ?? "prospect",
    owner: partner?.owner ?? "", contact_name: partner?.contact_name ?? "", contact_email: partner?.contact_email ?? "",
    summary: partner?.summary ?? "",
  };
}

/** Mirrors backend PartnerCreate limits so most problems are caught before a request. */
function validate(form: FormState): Partial<Record<keyof FormState, string>> {
  const errors: Partial<Record<keyof FormState, string>> = {};
  if (form.name.trim().length < 2) errors.name = "Enter at least 2 characters.";
  if (form.category.trim().length < 2) errors.category = "Enter at least 2 characters.";
  if (form.owner.trim().length < 2) errors.owner = "Enter the responsible owner (at least 2 characters).";
  if (form.contact_email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.contact_email.trim())) errors.contact_email = "Enter a valid email address or leave it blank.";
  return errors;
}

export default function PartnerForm({ partner, onSaved, onCancel }: { partner?: Partner; onSaved: (saved: Partner) => void; onCancel: () => void }) {
  const [form, setForm] = useState<FormState>(() => initialState(partner));
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [submitError, setSubmitError] = useState("");
  const [saving, setSaving] = useState(false);
  const set = (field: keyof FormState) => (value: string) => setForm((current) => ({ ...current, [field]: value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    // Blank optional fields are sent as null so an edit can clear them.
    const payload = {
      name: form.name.trim(), category: form.category.trim(), status: form.status, owner: form.owner.trim(),
      contact_name: form.contact_name.trim() || null, contact_email: form.contact_email.trim() || null,
      summary: form.summary.trim() || (partner ? "" : "No summary supplied."),
    };
    setSaving(true);
    setSubmitError("");
    try {
      onSaved(partner ? await api.partners.update(partner.id, payload) : await api.partners.create(payload));
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Could not save the partner.");
    } finally {
      setSaving(false);
    }
  }

  const field = (name: keyof FormState, label: string, input: JSX.Element, hint?: string) => (
    <label className={`form-field${errors[name] ? " has-error" : ""}`}>
      <span>{label}</span>{input}
      {errors[name] ? <small className="field-error" id={`${name}-error`}>{errors[name]}</small> : hint && <small>{hint}</small>}
    </label>
  );
  const describedBy = (name: keyof FormState) => (errors[name] ? `${name}-error` : undefined);

  return <form className="form-grid" onSubmit={(e) => void submit(e)} noValidate>
    {field("name", "Partner name *", <input value={form.name} onChange={(e) => set("name")(e.target.value)} maxLength={160} required aria-invalid={Boolean(errors.name)} aria-describedby={describedBy("name")} autoFocus />)}
    {field("category", "Category *", <input value={form.category} onChange={(e) => set("category")(e.target.value)} maxLength={100} required aria-invalid={Boolean(errors.category)} aria-describedby={describedBy("category")} placeholder="e.g. Training & curriculum" />)}
    {field("status", "Relationship status", <select value={form.status} onChange={(e) => set("status")(e.target.value)}>{STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}</select>)}
    {field("owner", "Responsible owner *", <input value={form.owner} onChange={(e) => set("owner")(e.target.value)} maxLength={120} required aria-invalid={Boolean(errors.owner)} aria-describedby={describedBy("owner")} />)}
    {field("contact_name", "Contact name", <input value={form.contact_name} onChange={(e) => set("contact_name")(e.target.value)} maxLength={120} />)}
    {field("contact_email", "Contact email", <input type="email" value={form.contact_email} onChange={(e) => set("contact_email")(e.target.value)} maxLength={254} aria-invalid={Boolean(errors.contact_email)} aria-describedby={describedBy("contact_email")} />)}
    <div className="form-wide">{field("summary", "Summary", <textarea value={form.summary} onChange={(e) => set("summary")(e.target.value)} maxLength={1200} rows={3} />, "Record verified facts only.")}</div>
    {submitError && <p className="form-wide form-error" role="alert">{submitError}</p>}
    <div className="form-wide form-actions">
      <button type="button" className="button button-secondary" onClick={onCancel} disabled={saving}>Cancel</button>
      <button type="submit" className="button button-primary" disabled={saving}>{saving ? "Saving…" : partner ? "Save changes" : "Create partner"}</button>
    </div>
  </form>;
}
