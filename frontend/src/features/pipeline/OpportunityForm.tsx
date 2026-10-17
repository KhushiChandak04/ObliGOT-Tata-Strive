import { useState, type FormEvent } from "react";
import { api } from "../../services/functions.service";
import { STAGES } from "../../lib/pipeline";
import type { Opportunity, OpportunityStage, Partner } from "../../types";

type FormState = { partner_id: string; title: string; stage: OpportunityStage; owner: string; next_step: string; next_step_date: string };
type Errors = Partial<Record<keyof FormState, string>>;

function validate(form: FormState): Errors {
  const errors: Errors = {};
  if (!form.partner_id) errors.partner_id = "Choose the partner this opportunity belongs to.";
  if (form.title.trim().length < 2) errors.title = "Enter at least 2 characters.";
  if (form.owner.trim().length < 2) errors.owner = "Enter the responsible owner (at least 2 characters).";
  return errors;
}

/** Create or edit an opportunity. Editing also offers delete with an explicit confirmation step. */
export default function OpportunityForm({ opportunity, partners, defaultPartnerId, onSaved, onDeleted, onCancel }: {
  opportunity?: Opportunity; partners: Partner[]; defaultPartnerId?: string;
  onSaved: (saved: Opportunity) => void; onDeleted?: () => void; onCancel: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => ({
    partner_id: opportunity?.partner_id ?? defaultPartnerId ?? "", title: opportunity?.title ?? "",
    stage: opportunity?.stage ?? "identified", owner: opportunity?.owner ?? "",
    next_step: opportunity?.next_step ?? "", next_step_date: opportunity?.next_step_date ?? "",
  }));
  const [errors, setErrors] = useState<Errors>({});
  const [submitError, setSubmitError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const set = (field: keyof FormState) => (value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => (current[field] ? { ...current, [field]: undefined } : current));
  };

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    const payload = {
      partner_id: form.partner_id, title: form.title.trim(), stage: form.stage, owner: form.owner.trim(),
      next_step: form.next_step.trim(), next_step_date: form.next_step_date || null,
    };
    setBusy(true); setSubmitError("");
    try {
      onSaved(opportunity ? await api.opportunities.update(opportunity.id, payload) : await api.opportunities.create(payload));
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Could not save the opportunity.");
    } finally { setBusy(false); }
  }

  async function remove() {
    if (!opportunity) return;
    setBusy(true); setSubmitError("");
    try { await api.opportunities.remove(opportunity.id); onDeleted?.(); }
    catch (err) { setSubmitError(err instanceof Error ? err.message : "Could not delete the opportunity."); }
    finally { setBusy(false); }
  }

  const field = (name: keyof FormState, label: string, input: JSX.Element, hint?: string) => (
    <label className={`form-field${errors[name] ? " has-error" : ""}`}>
      <span>{label}</span>{input}
      {errors[name] ? <small className="field-error" id={`opp-${name}-error`}>{errors[name]}</small> : hint && <small>{hint}</small>}
    </label>
  );
  const invalid = (name: keyof FormState) => ({ "aria-invalid": Boolean(errors[name]), "aria-describedby": errors[name] ? `opp-${name}-error` : undefined });

  return <form className="form-grid" onSubmit={(e) => void submit(e)} noValidate>
    <div className="form-wide">{field("partner_id", "Partner *", <select value={form.partner_id} onChange={(e) => set("partner_id")(e.target.value)} {...invalid("partner_id")}><option value="">Select a partner…</option>{partners.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>)}</div>
    <div className="form-wide">{field("title", "Opportunity title *", <input value={form.title} onChange={(e) => set("title")(e.target.value)} maxLength={200} {...invalid("title")} autoFocus />)}</div>
    {field("stage", "Stage", <select value={form.stage} onChange={(e) => set("stage")(e.target.value)}>{STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select>, "Stages record status only; they never imply a signed agreement.")}
    {field("owner", "Responsible owner *", <input value={form.owner} onChange={(e) => set("owner")(e.target.value)} maxLength={120} {...invalid("owner")} />)}
    {field("next_step", "Next step", <input value={form.next_step} onChange={(e) => set("next_step")(e.target.value)} maxLength={500} />)}
    {field("next_step_date", "Next step date", <input type="date" value={form.next_step_date} onChange={(e) => set("next_step_date")(e.target.value)} />)}
    {submitError && <p className="form-wide form-error" role="alert">{submitError}</p>}
    <div className="form-wide form-actions form-actions-split">
      {opportunity && onDeleted ? (confirmingDelete
        ? <span className="inline-confirm">Delete this opportunity? <button type="button" className="button button-danger" onClick={() => void remove()} disabled={busy}>Confirm delete</button><button type="button" className="text-button" onClick={() => setConfirmingDelete(false)} disabled={busy}>Keep</button></span>
        : <button type="button" className="text-button danger-text" onClick={() => setConfirmingDelete(true)} disabled={busy}>Delete opportunity</button>) : <span />}
      <span className="form-actions">
        <button type="button" className="button button-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
        <button type="submit" className="button button-primary" disabled={busy}>{busy ? "Saving…" : opportunity ? "Save changes" : "Create opportunity"}</button>
      </span>
    </div>
  </form>;
}
