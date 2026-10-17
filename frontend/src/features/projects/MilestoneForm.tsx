import { useState, type FormEvent } from "react";
import FormField from "../../components/ui/FormField";
import { api } from "../../services/functions.service";
import { EnumOptions } from "../../lib/options";
import type { Milestone, MilestoneStatus } from "../../types";

type FormState = { title: string; due_date: string; status: MilestoneStatus; completed_date: string; owner: string };
type Errors = Partial<Record<keyof FormState, string>>;

function validate(form: FormState): Errors {
  const errors: Errors = {};
  if (form.title.trim().length < 2) errors.title = "Enter at least 2 characters.";
  if (form.status === "completed" && !form.completed_date) errors.completed_date = "Enter the date the milestone was actually completed.";
  return errors;
}

/**
 * Create or edit a milestone. `markComplete` opens the form with status Completed so the user records the
 * actual completion date themselves; the app never assumes it.
 */
export default function MilestoneForm({ projectId, milestone, markComplete, onSaved, onDeleted, onCancel }: {
  projectId: string; milestone?: Milestone; markComplete?: boolean;
  onSaved: (saved: Milestone) => void; onDeleted?: () => void; onCancel: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => ({
    title: milestone?.title ?? "", due_date: milestone?.due_date ?? "", owner: milestone?.owner ?? "",
    status: markComplete ? "completed" : milestone?.status ?? "planned", completed_date: milestone?.completed_date ?? "",
  }));
  const [errors, setErrors] = useState<Errors>({});
  const [submitError, setSubmitError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const set = (field: keyof FormState) => (value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => (current[field] ? { ...current, [field]: undefined } : current));
  };
  const completed = form.status === "completed";

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    const payload = {
      project_id: projectId, title: form.title.trim(), due_date: form.due_date || null, status: form.status,
      // The backend only accepts a completion date on completed milestones.
      completed_date: completed ? form.completed_date : null, owner: form.owner.trim() || "Unassigned",
    };
    setBusy(true); setSubmitError("");
    try { onSaved(milestone ? await api.milestones.update(milestone.id, payload) : await api.milestones.create(payload)); }
    catch (err) { setSubmitError(err instanceof Error ? err.message : "Could not save the milestone."); }
    finally { setBusy(false); }
  }

  async function remove() {
    if (!milestone) return;
    setBusy(true); setSubmitError("");
    try { await api.milestones.remove(milestone.id); onDeleted?.(); }
    catch (err) { setSubmitError(err instanceof Error ? err.message : "Could not delete the milestone."); }
    finally { setBusy(false); }
  }

  const field = (name: keyof FormState, label: string, input: JSX.Element, hint?: string) => (
    <FormField id={`ms-${name}`} label={label} error={errors[name]} hint={hint}>{input}</FormField>
  );

  return <form className="form-grid" onSubmit={(e) => void submit(e)} noValidate>
    <div className="form-wide">{field("title", "Milestone *", <input value={form.title} onChange={(e) => set("title")(e.target.value)} maxLength={200} autoFocus={!markComplete} />)}</div>
    {field("due_date", "Due date", <input type="date" value={form.due_date} onChange={(e) => set("due_date")(e.target.value)} />)}
    {field("status", "Status", <select value={form.status} onChange={(e) => set("status")(e.target.value)}><EnumOptions group="milestone_status" current={form.status} /></select>)}
    {completed && field("completed_date", "Completed on *", <input type="date" value={form.completed_date} onChange={(e) => set("completed_date")(e.target.value)} autoFocus={markComplete} />, "The actual completion date, as recorded by the team.")}
    {field("owner", "Responsible owner", <input value={form.owner} onChange={(e) => set("owner")(e.target.value)} maxLength={120} placeholder="Unassigned" />)}
    {submitError && <p className="form-wide form-error" role="alert">{submitError}</p>}
    <div className="form-wide form-actions form-actions-split">
      {milestone && onDeleted ? (confirmingDelete
        ? <span className="inline-confirm">Delete this milestone? <button type="button" className="button button-danger" onClick={() => void remove()} disabled={busy}>Confirm delete</button><button type="button" className="text-button" onClick={() => setConfirmingDelete(false)} disabled={busy}>Keep</button></span>
        : <button type="button" className="text-button danger-text" onClick={() => setConfirmingDelete(true)} disabled={busy}>Delete milestone</button>) : <span />}
      <span className="form-actions">
        <button type="button" className="button button-secondary" onClick={onCancel} disabled={busy}>Cancel</button>
        <button type="submit" className="button button-primary" disabled={busy}>{busy ? "Saving…" : markComplete ? "Mark complete" : milestone ? "Save changes" : "Add milestone"}</button>
      </span>
    </div>
  </form>;
}
