import { useState, type FormEvent } from "react";
import FormField from "../../components/ui/FormField";
import { api } from "../../services/functions.service";
import { EnumOptions } from "../../lib/options";
import type { Partner, Project, RecordStatus } from "../../types";

type FormState = { partner_id: string; name: string; status: RecordStatus; owner: string; start_date: string; end_date: string; milestone_summary: string };
type Errors = Partial<Record<keyof FormState, string>>;

function validate(form: FormState): Errors {
  const errors: Errors = {};
  if (form.name.trim().length < 2) errors.name = "Enter at least 2 characters.";
  if (form.start_date && form.end_date && form.end_date < form.start_date) errors.end_date = "End date must be on or after the start date.";
  return errors;
}

/** Create or edit a project. A project may exist without a partner; delete is blocked server-side while records are linked. */
export default function ProjectForm({ project, partners, defaultPartnerId, onSaved, onDeleted, onCancel }: {
  project?: Project; partners: Partner[]; defaultPartnerId?: string;
  onSaved: (saved: Project) => void; onDeleted?: () => void; onCancel: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => ({
    partner_id: project?.partner_id ?? defaultPartnerId ?? "", name: project?.name ?? "", status: project?.status ?? "planned",
    owner: project?.owner ?? "", start_date: project?.start_date ?? "", end_date: project?.end_date ?? "",
    milestone_summary: project?.milestone_summary ?? "",
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
      partner_id: form.partner_id || null, name: form.name.trim(), status: form.status, owner: form.owner.trim() || "Unassigned",
      start_date: form.start_date || null, end_date: form.end_date || null, milestone_summary: form.milestone_summary.trim(),
    };
    setBusy(true); setSubmitError("");
    try { onSaved(project ? await api.projects.update(project.id, payload) : await api.projects.create(payload)); }
    catch (err) { setSubmitError(err instanceof Error ? err.message : "Could not save the project."); }
    finally { setBusy(false); }
  }

  async function remove() {
    if (!project) return;
    setBusy(true); setSubmitError("");
    try { await api.projects.remove(project.id); onDeleted?.(); }
    catch (err) { setSubmitError(err instanceof Error ? err.message : "Could not delete the project."); setConfirmingDelete(false); }
    finally { setBusy(false); }
  }

  const field = (name: keyof FormState, label: string, input: JSX.Element, hint?: string) => (
    <FormField id={`prj-${name}`} label={label} error={errors[name]} hint={hint}>{input}</FormField>
  );

  return <form className="form-grid" onSubmit={(e) => void submit(e)} noValidate>
    <div className="form-wide">{field("name", "Project name *", <input value={form.name} onChange={(e) => set("name")(e.target.value)} maxLength={200} autoFocus />)}</div>
    {field("partner_id", "Partner", <select value={form.partner_id} onChange={(e) => set("partner_id")(e.target.value)} disabled={Boolean(defaultPartnerId) && !project}><option value="">No partner</option>{partners.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>, project ? "Cannot be changed while milestones or other records are linked." : undefined)}
    {field("status", "Status", <select value={form.status} onChange={(e) => set("status")(e.target.value)}><EnumOptions group="project_status" current={form.status} /></select>)}
    {field("start_date", "Start date", <input type="date" value={form.start_date} onChange={(e) => set("start_date")(e.target.value)} />)}
    {field("end_date", "End date", <input type="date" value={form.end_date} onChange={(e) => set("end_date")(e.target.value)} />)}
    {field("owner", "Responsible owner", <input value={form.owner} onChange={(e) => set("owner")(e.target.value)} maxLength={120} placeholder="Unassigned" />)}
    <div className="form-wide">{field("milestone_summary", "Progress note", <textarea value={form.milestone_summary} onChange={(e) => set("milestone_summary")(e.target.value)} rows={2} maxLength={1000} />, "Short, factual status note. Track dated milestones separately.")}</div>
    {submitError && <p className="form-wide form-error" role="alert">{submitError}</p>}
    <div className="form-wide form-actions form-actions-split">
      {project && onDeleted ? (confirmingDelete
        ? <span className="inline-confirm">Delete this project? <button type="button" className="button button-danger" onClick={() => void remove()} disabled={busy}>Confirm delete</button><button type="button" className="text-button" onClick={() => setConfirmingDelete(false)} disabled={busy}>Keep</button></span>
        : <button type="button" className="text-button danger-text" onClick={() => setConfirmingDelete(true)} disabled={busy}>Delete project</button>) : <span />}
      <span className="form-actions">
        <button type="button" className="button button-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
        <button type="submit" className="button button-primary" disabled={busy}>{busy ? "Saving…" : project ? "Save changes" : "Create project"}</button>
      </span>
    </div>
  </form>;
}
