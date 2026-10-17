import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import FormField from "../../components/ui/FormField";
import StatusBadge from "../../components/ui/StatusBadge";
import { api } from "../../services/functions.service";
import { CATEGORY_LABELS, DECISION_LABELS, SEVERITY_LABELS, alertTiming } from "../../lib/alerts";
import { formatDate, titleCase } from "../../lib/utils";

const showValue = (value: string | number) => typeof value === "number" ? value.toLocaleString("en-IN")
  : /^\d{4}-\d{2}-\d{2}$/.test(value) ? formatDate(value) : /^[a-z]+(_[a-z]+)*$/.test(value) ? titleCase(value) : value;
import type { Alert, Priority } from "../../types";

type Mode = "none" | "defer" | "dismiss" | "task";

const RECORD_LINKS: Record<string, string> = {
  agreements: "/agreements", opportunities: "/pipeline", milestones: "/projects", reports: "/reports", finance: "/finance", actions: "/actions",
};

/** Next calendar day after an ISO date, for the defer date picker's minimum (the backend validates authoritatively). */
function nextDay(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

export default function AlertDetail({ alert, asOf, partnerName, related, onChanged, onOpenRelated }: {
  alert: Alert; asOf: string; partnerName?: (id: string) => string | undefined; related: Alert[];
  onChanged: (message: string) => void; onOpenRelated: (alert: Alert) => void;
}) {
  const [mode, setMode] = useState<Mode>("none");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [deferUntil, setDeferUntil] = useState("");
  const [reason, setReason] = useState("");
  const [task, setTask] = useState({ title: `${alert.rule_title}: ${alert.record_title}`, owner: alert.owner === "Unassigned" ? "" : alert.owner, due_date: "", priority: alert.priority.level as Priority });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const partner = alert.partner_id ? partnerName?.(alert.partner_id) ?? alert.partner_id : null;
  const recordEvidence = alert.evidence.filter((e) => e.source === "record");
  const computedEvidence = alert.evidence.filter((e) => e.source === "computed");

  async function run(action: () => Promise<unknown>, message: string) {
    setBusy(true); setError("");
    try { await action(); onChanged(message); }
    catch (err) { setError(err instanceof Error ? err.message : "The request failed."); }
    finally { setBusy(false); }
  }
  function submitDefer(e: FormEvent) {
    e.preventDefault();
    if (!deferUntil) { setFieldErrors({ defer: "Choose the date to bring this alert back." }); return; }
    void run(() => api.alerts.review(alert.id, { decision: "deferred", deferred_until: deferUntil }), `Deferred until ${formatDate(deferUntil)}.`);
  }
  function submitDismiss(e: FormEvent) {
    e.preventDefault();
    if (reason.trim().length < 5) { setFieldErrors({ reason: "Explain why (at least 5 characters). The reason is recorded in the activity log." }); return; }
    void run(() => api.alerts.review(alert.id, { decision: "dismissed", reason: reason.trim() }), "Alert dismissed. It returns automatically if the record changes.");
  }
  function submitTask(e: FormEvent) {
    e.preventDefault();
    const errors: Record<string, string> = {};
    if (task.title.trim().length < 3) errors.title = "Enter at least 3 characters.";
    if (task.owner.trim().length < 2) errors.owner = "Assign a responsible owner.";
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;
    void run(() => api.alerts.createTask(alert.id, { title: task.title.trim(), owner: task.owner.trim(), due_date: task.due_date || null, priority: task.priority }),
      `Task created and assigned to ${task.owner.trim()}.`);
  }
  const switchMode = (next: Mode) => { setMode(next); setError(""); setFieldErrors({}); };

  return <div className="alert-detail">
    <div className="alert-detail-head">
      <StatusBadge value={alert.priority.level} label={`${titleCase(alert.priority.level)} priority`} />
      <span className="muted">{SEVERITY_LABELS[alert.severity]} · {CATEGORY_LABELS[alert.category]} · {alertTiming(alert)}</span>
    </div>
    <h3 className="alert-detail-title">{alert.record_title}</h3>
    <p className="alert-detail-rule"><strong>{alert.rule_title}.</strong> {alert.rule_description} <span className="muted">Rule {alert.rule_id}.</span></p>
    {alert.source_label === "demo" && <p className="muted">Based on a fictional demo record.</p>}

    {alert.review && <p className="review-banner" role="status"><strong>{DECISION_LABELS[alert.review.decision]}</strong> by {alert.review.reviewer} on {formatDate(alert.review.reviewed_at.slice(0, 10))}
      {alert.review.deferred_until && <> until {formatDate(alert.review.deferred_until)}</>}{alert.review.reason && <>: “{alert.review.reason}”</>}
      {alert.review.task_id && <> · <Link className="text-link" to={`/actions?task=${encodeURIComponent(alert.review.task_id)}`}>View task</Link></>}</p>}
    {alert.previous_review && <p className="review-banner stale" role="status">Previously {DECISION_LABELS[alert.previous_review.decision].toLowerCase()} by {alert.previous_review.reviewer}. {alert.previous_review.stale_reason}</p>}

    <dl className="detail-facts">
      <div><dt>Partner</dt><dd>{partner ? <Link className="text-link" to={`/partners/${alert.partner_id}`}>{partner}</Link> : "Not linked"}</dd></div>
      <div><dt>Responsible owner</dt><dd>{alert.owner}</dd></div>
      <div><dt>Due / expiry date</dt><dd>{alert.due_date ? formatDate(alert.due_date) : "Not recorded"}</dd></div>
      <div><dt>Record</dt><dd>{RECORD_LINKS[alert.record_type] ? <Link className="text-link" to={RECORD_LINKS[alert.record_type]}>{titleCase(alert.record_type)}</Link> : titleCase(alert.record_type)}</dd></div>
    </dl>

    <section className="evidence-panel" aria-labelledby={`ev-${alert.id}`}>
      <h4 id={`ev-${alert.id}`}>Evidence</h4>
      <div className="evidence-columns">
        <div><h5>From the record</h5><dl>{recordEvidence.map((e) => <div key={e.label}><dt>{e.label}</dt><dd>{showValue(e.value)}</dd></div>)}</dl></div>
        {computedEvidence.length > 0 && <div><h5>Computed by the rule (as of {formatDate(asOf)})</h5><dl>{computedEvidence.map((e) => <div key={e.label}><dt>{e.label}</dt><dd>{showValue(e.value)}</dd></div>)}</dl></div>}
      </div>
    </section>

    <div className="detail-two-col">
      <section><h4>Why it matters</h4><p>{alert.why_it_matters}</p><h4>Recommended action</h4><p>{alert.recommended_action}</p></section>
      <section aria-labelledby={`score-${alert.id}`}><h4 id={`score-${alert.id}`}>Priority score: {alert.priority.score}</h4>
        <table className="score-table"><tbody>{alert.priority.factors.map((f) => <tr key={f.label}><td>{f.label}</td><td className="numeric">{f.points > 0 ? `+${f.points}` : f.points}</td></tr>)}</tbody></table>
        <p className="muted">Illustrative business rule (high ≥ 60, medium ≥ 35), not a prediction.</p></section>
    </div>

    {related.length > 0 && <section><h4>Related alerts for this partner ({related.length})</h4>
      <ul className="related-list">{related.map((r) => <li key={r.id}><button className="text-button" onClick={() => onOpenRelated(r)}>{r.rule_title}: {r.record_title}</button> <span className="muted">· {titleCase(r.priority.level)} · {alertTiming(r)}</span></li>)}</ul></section>}

    <section className="review-actions" aria-label="Review this alert">
      {error && <p className="form-error" role="alert">{error}</p>}
      {mode === "none" && <div className="review-buttons">
        <button className="button button-primary" onClick={() => switchMode("task")} disabled={busy || alert.review?.decision === "task_created"}>Create task</button>
        <button className="button button-secondary" onClick={() => void run(() => api.alerts.review(alert.id, { decision: "acknowledged" }), "Alert acknowledged.")} disabled={busy || alert.review?.decision === "acknowledged"}>Acknowledge</button>
        <button className="button button-secondary" onClick={() => switchMode("defer")} disabled={busy}>Defer</button>
        <button className="button button-secondary" onClick={() => switchMode("dismiss")} disabled={busy}>Dismiss</button>
        {alert.review && <button className="text-button" onClick={() => void run(() => api.alerts.clearReview(alert.id), "Review cleared; the alert is open again.")} disabled={busy}>Reopen (clear review)</button>}
      </div>}
      {mode === "defer" && <form className="inline-form" onSubmit={submitDefer} noValidate>
        <FormField id="defer-until" label="Bring back on" error={fieldErrors.defer} hint="The alert is hidden until this date, or sooner if the record changes."><input type="date" min={nextDay(asOf)} value={deferUntil} onChange={(e) => setDeferUntil(e.target.value)} autoFocus /></FormField>
        <div className="form-actions"><button type="button" className="button button-secondary" onClick={() => switchMode("none")} disabled={busy}>Back</button><button className="button button-primary" disabled={busy}>{busy ? "Saving…" : "Defer alert"}</button></div>
      </form>}
      {mode === "dismiss" && <form className="inline-form" onSubmit={submitDismiss} noValidate>
        <FormField id="dismiss-reason" label="Reason for dismissing *" error={fieldErrors.reason} hint="Dismissal applies only while the record is unchanged."><textarea rows={2} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} autoFocus /></FormField>
        <div className="form-actions"><button type="button" className="button button-secondary" onClick={() => switchMode("none")} disabled={busy}>Back</button><button className="button button-danger" disabled={busy}>{busy ? "Saving…" : "Dismiss alert"}</button></div>
      </form>}
      {mode === "task" && <form className="inline-form form-grid" onSubmit={submitTask} noValidate>
        <div className="form-wide"><FormField id="task-title" label="Task *" error={fieldErrors.title}><input value={task.title} maxLength={240} onChange={(e) => setTask({ ...task, title: e.target.value })} /></FormField></div>
        <FormField id="task-owner" label="Assign to *" error={fieldErrors.owner}><input value={task.owner} maxLength={120} onChange={(e) => setTask({ ...task, owner: e.target.value })} autoFocus /></FormField>
        <FormField id="task-due" label="Due date"><input type="date" value={task.due_date} onChange={(e) => setTask({ ...task, due_date: e.target.value })} /></FormField>
        <FormField id="task-priority" label="Priority" hint="Prefilled from the alert's priority."><select value={task.priority} onChange={(e) => setTask({ ...task, priority: e.target.value as Priority })}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></FormField>
        <p className="form-wide muted">The task copies this alert's evidence and recommended action. The alert stays open until the record itself is updated.</p>
        <div className="form-wide form-actions"><button type="button" className="button button-secondary" onClick={() => switchMode("none")} disabled={busy}>Back</button><button className="button button-primary" disabled={busy}>{busy ? "Creating…" : "Create task"}</button></div>
      </form>}
    </section>
  </div>;
}
