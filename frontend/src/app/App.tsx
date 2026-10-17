import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { repository, type Agreement, type Invoice, type PipelineItem, type PipelineStage, type Project, type Report } from "../data/repository";
import { api } from "../services/functions.service";
import { useResource } from "../lib/useResource";
import { CATEGORY_LABELS, todaysAlerts } from "../lib/alerts";
import type { ActionItem, Alert as ApiAlert, AnalyzeResponse, AlertEvidence, ImportPreview } from "../types";

/** View model for the reference UI, built from a rules-engine alert (GET /api/alerts). */
type Alert = {
  id: string;
  rule: string;
  ruleTitle: string;
  ruleDescription: string;
  partnerId: string | null;
  partner: string;
  title: string;
  priority: "High" | "Medium" | "Low";
  score: number;
  factors: { label: string; points: number }[];
  days: number | null;
  owner: string;
  category: string;
  facts: AlertEvidence[];
  computed: AlertEvidence[];
  why: string;
  recommendation: string;
  review: ApiAlert["review"];
  demo: boolean;
};

const toViewAlert = (alert: ApiAlert, partnerName: (id: string) => string | undefined): Alert => ({
  id: alert.id, rule: alert.rule_id, ruleTitle: alert.rule_title, ruleDescription: alert.rule_description,
  partnerId: alert.partner_id ?? null, partner: alert.partner_id ? partnerName(alert.partner_id) ?? alert.partner_id : "No partner linked",
  title: `${alert.rule_title}: ${alert.record_title}`, priority: alert.priority.level === "high" ? "High" : alert.priority.level === "medium" ? "Medium" : "Low",
  score: alert.priority.score, factors: alert.priority.factors, days: alert.days_remaining ?? null,
  owner: alert.owner, category: CATEGORY_LABELS[alert.category] ?? alert.category,
  facts: alert.evidence.filter((e) => e.source === "record"), computed: alert.evidence.filter((e) => e.source === "computed"),
  why: alert.why_it_matters, recommendation: alert.recommended_action, review: alert.review, demo: alert.source_label === "demo",
});

/** Short timing label from the backend's days_remaining; the browser does no deadline arithmetic. */
const timing = (alert: Alert) => alert.days === null ? "No date" : alert.days < 0 ? `${Math.abs(alert.days)}d overdue` : alert.days === 0 ? "Today" : `in ${alert.days}d`;
const isOpenTask = (task: ActionItem) => task.status === "open" || task.status === "in_review";

function Logo({ light = false }: { light?: boolean }) {
  return <span className={`logo${light ? " light" : ""}`}>Obli<i>GOT</i></span>;
}

function Landing() {
  const navigate = useNavigate();
  const [trace, setTrace] = useState(0);
  const lines = ["▸ Evaluating 214 stored records…", "✓ Rule MOU-EXP-01 fired", "  agreement.endDate = today+14d ISO", "  renewalStatus = (empty)", "⚠ Rule RPT-OVD-01 fired", "✓ Priority: HIGH (deterministic)", "▸ Gemini drafting follow-up…", "⏸ Waiting for human approval"];
  useEffect(() => {
    const timer = window.setInterval(() => setTrace((value) => value >= lines.length ? 0 : value + 1), 750);
    return () => window.clearInterval(timer);
  }, [lines.length]);
  return <div className="landing">
    <nav className="top-nav"><Logo /><div className="nav-actions"><a href="#how">How it works</a><a href="#why">Why ObliGOT</a><button className="btn outline" onClick={() => navigate("/auth")}>Sign in</button><button className="btn" onClick={() => navigate("/auth?mode=up")}>Get started</button></div></nav>
    <section className="hero"><div><span className="eyebrow">Partnership intelligence · Tata STRIVE</span><h1>Obligations? <span className="got">Got them.<b>GOT IT ✓</b></span></h1><p className="lead">MOUs, reports, invoices and UCs live in a dozen trackers. ObliGOT watches them all, explains what needs attention, and drafts the next move. Your team approves it.</p><div className="button-row"><button className="btn" onClick={() => navigate("/auth")}>Open the workspace →</button><a className="btn outline" href="#how">See the agent think</a></div></div><div className="agent"><div className="agent-bar"><span>● ● ●</span><b>obligot-agent · live trace</b></div><div className="trace mono">{lines.slice(0, trace).map((line, index) => <div key={line} className={index === 1 || index === 5 ? "ok" : index === 4 ? "warning" : ""}>{line}{index === lines.length - 1 && trace === lines.length ? <em className="cursor" /> : null}</div>)}</div></div></section>
    <div className="marquee"><div>MOU expiring ✦ Report overdue ✦ UC pending ✦ Invoice aging ✦ Milestone slipped ✦ Renewal due ✦ MOU expiring ✦ Report overdue ✦ UC pending ✦ Invoice aging ✦ Milestone slipped ✦ Renewal due ✦</div></div>
    <section className="section" id="how"><h2>Every alert answers five questions</h2><div className="flow">{[["Issue", "What was flagged by a rule"], ["Evidence", "The exact fields and dates"], ["Why it matters", "Plain-language impact"], ["Next action", "AI suggests, you decide"], ["Owner + due", "Tracked until resolved"]].map(([title, detail], index) => <div className="step" key={title}><b>0{index + 1}</b>{title}<small>{detail}</small></div>)}</div></section>
    <section className="section why" id="why"><div className="three"><InfoPanel className="green-panel" tag="DETERMINISTIC" title="Rules decide facts">Dates, deadlines and amounts are computed by code, never guessed by a model.</InfoPanel><InfoPanel className="card-panel" tag="GEMINI" title="AI explains & drafts">Summaries and follow-ups, clearly labelled as AI interpretation with uncertainty shown.</InfoPanel><InfoPanel className="bordo-panel" tag="HUMAN-IN-THE-LOOP" title="You approve">Nothing happens until a person reviews it. Every decision lands in the audit trail.</InfoPanel></div></section>
    <footer><Logo light /><span className="mono">Built for Tata STRIVE Code Odyssey 5.0 · Demo uses synthetic data</span></footer>
  </div>;
}

function InfoPanel({ className = "", tag, title, children }: { className?: string; tag: string; title: string; children: ReactNode }) {
  return <div className={`info-panel ${className}`}><span className="tag">{tag}</span><h3>{title}</h3><p>{children}</p></div>;
}

function Auth() {
  const navigate = useNavigate();
  const mode = new URLSearchParams(useLocation().search).get("mode") === "up";
  const [signup, setSignup] = useState(mode);
  return <div className="auth-page"><div className="auth-left"><Link to="/"><Logo light /></Link><h2>From commitments to accountability.</h2><span className="mono">Prototype screen. Production build uses Firebase Authentication.</span></div><div className="auth-right"><form className="auth-form" onSubmit={(event) => { event.preventDefault(); navigate("/dashboard"); }}><h2>{signup ? "Join the team" : "Welcome back"}</h2><p>Sign in to your partnership workspace.</p><div className="tabs"><button type="button" className={!signup ? "active" : ""} onClick={() => setSignup(false)}>Sign in</button><button type="button" className={signup ? "active" : ""} onClick={() => setSignup(true)}>Sign up</button></div>{signup && <label>Full name<input placeholder="Your name" /></label>}<label>Work email<input type="email" placeholder="you@tatastrive.org" required /></label><label>Password<input type="password" placeholder="••••••••" required /></label>{signup && <label>Role<input value="Manager" readOnly /></label>}<button className="btn submit" type="submit">{signup ? "Create account" : "Sign in"}</button></form></div></div>;
}

function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const workspace = useResource(async () => {
    const [alerts, tasks, partners] = await Promise.all([api.alerts.list(), api.actions.list(), api.partners.list()]);
    return { alerts, tasks, partners };
  }, []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const names = new Map((workspace.data?.partners ?? []).map((p) => [p.id, p.name]));
  const apiAlerts = workspace.data?.alerts.alerts ?? [];
  const sorted = apiAlerts.map((alert) => toViewAlert(alert, (id) => names.get(id)));  // already ordered by priority score
  const today = todaysAlerts(apiAlerts).map((alert) => toViewAlert(alert, (id) => names.get(id)));
  const open = sorted;
  const tasks = (workspace.data?.tasks ?? []).filter(isOpenTask);
  const selected = sorted.find((alert) => alert.id === selectedId) ?? null;
  const select = (alert: Alert) => { setNotice(""); setSelectedId(alert.id); };
  const changed = (message: string) => { setSelectedId(null); setNotice(message); workspace.reload(); };
  const page = location.pathname;
  const title = page === "/action-center" ? "Action Center" : page === "/partner-360" ? "Kaveri Retail Academy" : page === "/dashboard" ? "Good day, team." : page === "/pipeline" ? "Pipeline" : page === "/agreements" ? "Agreements" : page === "/projects" ? "Projects" : page === "/finance" ? "Finance" : page === "/reports" ? "Reports & UCs" : "Import";
  const eyebrow = page === "/dashboard" ? `Portfolio overview${workspace.data ? ` · rules evaluated ${formatDate(workspace.data.alerts.as_of)}` : ""}` : page === "/partner-360" ? "Partner 360" : page === "/action-center" ? "Live rule alerts" : "Synthetic demo data";
  const usesApi = page === "/dashboard" || page === "/action-center";
  return <div className="app-shell"><aside className="sidebar"><Logo light /><nav>{[{to:"/dashboard", label:"Dashboard"}, {to:"/action-center", label:"Action Center", count:open.length}, {to:"/partner-360", label:"Partner 360"}, {to:"/pipeline", label:"Pipeline"}, {to:"/agreements", label:"Agreements"}, {to:"/projects", label:"Projects"}, {to:"/finance", label:"Finance"}, {to:"/reports", label:"Reports & UCs"}, {to:"/import", label:"Import"}].map((item) => <NavLink key={item.to} to={item.to} className={({isActive}) => isActive ? "active" : ""}>{item.label}{item.count ? <span className="pill high">{item.count}</span> : null}</NavLink>)}</nav><button className="logout" onClick={() => navigate("/")}>↩ Log out</button><small>{workspace.data?.alerts.alerts.some((alert) => alert.source_label === "demo") ? "Fictional demo records" : "Synthetic demo data"}</small></aside><main className="app-main"><div className="page-header"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1></div>
    {usesApi && workspace.error && <div className="api-state error" role="alert"><b>Could not reach the ObliGOT API.</b><span>{workspace.error.message}</span><button className="btn small-btn" onClick={workspace.reload}>Retry</button></div>}
    {usesApi && workspace.loading && !workspace.data && <p className="api-state" role="status">Evaluating rules on stored records…</p>}
    {usesApi && notice && <p className="api-state success" role="status">{notice}</p>}
    {page === "/dashboard" && workspace.data && <Dashboard open={open} sorted={today} tasks={tasks} onSelect={select} />}{page === "/action-center" && workspace.data && <ActionCenter open={open} sorted={sorted} tasks={tasks} hidden={workspace.data.alerts.counts.hidden_by_review} onSelect={select} onChanged={changed} />}{page === "/partner-360" && <Partner360 open={open} onSelect={select} />}{page === "/pipeline" && <PipelinePage />}{page === "/agreements" && <AgreementsPage />}{page === "/projects" && <ProjectsPage />}{page === "/finance" && <FinancePage />}{page === "/reports" && <ReportsPage />}{page === "/import" && <ImportPage />}</main>{selected && workspace.data && <Drawer alert={selected} asOf={workspace.data.alerts.as_of} onClose={() => setSelectedId(null)} onChanged={changed} />}</div>;
}

function AlertRow({ alert, index, onSelect }: { alert: Alert; index: number; onSelect: (alert: Alert) => void }) {
  return <button className="alert-row" onClick={() => onSelect(alert)} aria-label={`${alert.partner}: ${alert.title}. ${alert.priority} priority. Open details`}><strong>{index + 1}</strong><span className="alert-copy"><b>{alert.partner}</b><small>{alert.title} · {alert.owner}{alert.review ? ` · ${alert.review.decision.replace("_", " ")}` : ""}</small></span><span className={`pill ${alert.priority === "High" ? "high" : "outline-pill"}`}>{alert.priority}</span><span className="pill outline-pill">{timing(alert)}</span></button>;
}

function Dashboard({ open, sorted, tasks, onSelect }: { open: Alert[]; sorted: Alert[]; tasks: ActionItem[]; onSelect: (alert: Alert) => void }) {
  const overdue = open.filter((alert) => alert.days !== null && alert.days < 0).length;
  const expiring = open.filter((alert) => alert.rule === "MOU_EXPIRING" && alert.days !== null && alert.days <= 30).length;
  const followUps = tasks.filter((task) => task.source_alert_id).length;
  const families = Object.entries(open.reduce<Record<string, number>>((result, alert) => { result[alert.category] = (result[alert.category] || 0) + 1; return result; }, {}));
  const max = Math.max(1, ...families.map(([, count]) => count));
  return <><div className="kpis"><Kpi value={open.length} label="Open alerts" /><Kpi value={overdue} label="Overdue items" hot /><Kpi value={expiring} label="MOUs expiring ≤30d" /><Kpi value={followUps} label="Open follow-ups from alerts" /></div><div className="grid2"><section className="box"><h3>Today’s 5</h3>{sorted.map((alert, index) => <AlertRow key={alert.id} alert={alert} index={index} onSelect={onSelect} />)}{!sorted.length && <p>All clear. Every open alert already has a follow-up, or no record triggers a rule.</p>}</section><section className="box"><h3>Alerts by category</h3>{families.map(([name, count]) => <div className="bar-row" key={name}><span>{name}</span><i style={{ width: `${count / max * 55}%` }} /><b>{count}</b></div>)}{!families.length && <p>No open alerts.</p>}</section></div></>;
}

function Kpi({ value, label, hot = false }: { value: number; label: string; hot?: boolean }) { return <div className={`kpi ${hot ? "hot" : ""}`}><b>{value}</b><span>{label}</span></div>; }
function ActionCenter({ open, sorted, tasks, hidden, onSelect, onChanged }: { open: Alert[]; sorted: Alert[]; tasks: ActionItem[]; hidden: number; onSelect: (alert: Alert) => void; onChanged: (message: string) => void }) {
  const [error, setError] = useState("");
  const done = async (task: ActionItem) => {
    setError("");
    try { await api.actions.update(task.id, { status: "done" }); onChanged(`Marked “${task.title}” done. The alert clears when the underlying record is updated.`); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not update the task."); }
  };
  return <><section className="box"><h3>All outstanding ({open.length})</h3>{hidden > 0 && <small>{hidden} deferred or dismissed alert{hidden === 1 ? " is" : "s are"} hidden until the date passes or the record changes.</small>}{sorted.map((alert, index) => <AlertRow key={alert.id} alert={alert} index={index} onSelect={onSelect} />)}{!sorted.length && <p>No open alerts.</p>}</section><section className="box task-box"><h3>Follow-up tasks</h3>{error && <p className="api-state error" role="alert">{error}</p>}{tasks.map((task) => <div className="task-row" key={task.id}><span>{task.title}<small> · {task.owner ?? "Unassigned"}{task.due_date ? ` · due ${formatDate(task.due_date)}` : ""}</small></span><button className="btn small-btn" onClick={() => void done(task)} aria-label={`Mark ${task.title} done`}>Mark done</button></div>)}{!tasks.length && <small>None yet. Create one from an alert.</small>}</section></>;
}
// Synthetic Partner 360 placeholder (teammate's reference UI); wired to the API in Step 8c.
const dateFromToday = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
};
function Partner360({ open, onSelect }: { open: Alert[]; onSelect: (alert: Alert) => void }) { return <div className="grid2"><section className="box"><h3>MOU timeline</h3><div className="timeline"><i /><em /></div><div className="detail-row"><span>Start</span><span>{dateFromToday(-350)}</span></div><div className="detail-row"><span>End</span><span>{dateFromToday(14)}</span></div><div className="detail-row"><span>Renewal</span><span>— not recorded</span></div></section><section className="box"><h3>Open alerts</h3>{open.filter((alert) => alert.partner === "Kaveri Retail Academy").map((alert, index) => <AlertRow key={alert.id} alert={alert} index={index} onSelect={onSelect} />)}</section></div>; }

const stages: PipelineStage[] = ["Opportunity", "Qualification", "Proposal", "Approval", "MOU", "Implementation", "Renewal", "Closure"];
const formatDate = (value: string | null): string => value ? new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value)) : "Not recorded";
const money = (value: number): string => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
function TableState({ message }: { message: string }) { return <p className="table-state">{message}</p>; }
function PipelinePage() {
  const [items, setItems] = useState<PipelineItem[]>(repository.pipeline);
  const move = (item: PipelineItem) => { const index = stages.indexOf(item.stage); if (index < stages.length - 1) setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, stage: stages[index + 1] } : entry)); };
  return <div className="pipeline-grid">{stages.map((stage) => { const column = items.filter((item) => item.stage === stage); return <section className="pipeline-column" key={stage}><h3>{stage}<span className="pill">{column.length}</span></h3>{column.length ? column.map((item) => <div className="pipeline-card" key={item.id}><b>{item.partner}</b><small>{item.owner}</small><p>{item.nextAction}</p><span className="mono">{formatDate(item.dueDate)}</span>{stage !== "Closure" && <button className="btn small-btn" onClick={() => move(item)}>Move to next stage</button>}</div>) : <TableState message="No opportunities" />}</section>; })}</div>;
}

function AgreementsPage() {
  const [query, setQuery] = useState(""); const [status, setStatus] = useState("All");
  const filtered = repository.agreements.filter((agreement) => `${agreement.partner} ${agreement.reference}`.toLowerCase().includes(query.toLowerCase()) && (status === "All" || agreement.status === status));
  const buckets = [0, 31, 61].map((minimum, index) => ({ label: `${minimum}-${index === 0 ? 30 : index === 1 ? 60 : 90} days`, count: repository.agreements.filter((agreement) => { const days = Math.ceil((new Date(agreement.endDate).getTime() - Date.now()) / 86400000); return days >= minimum && days <= (index === 0 ? 30 : index === 1 ? 60 : 90); }).length }));
  return <><div className="radar">{buckets.map((bucket) => <div key={bucket.label}><b>{bucket.count}</b><span>Expiring in {bucket.label}</span></div>)}</div><section className="box"><div className="toolbar"><input className="search" placeholder="Search partner or reference" value={query} onChange={(event) => setQuery(event.target.value)} /><select value={status} onChange={(event) => setStatus(event.target.value)}><option>All</option><option>Active</option><option>Expired</option><option>Draft</option></select></div><DataTable headers={["Partner", "Reference", "Status", "Start", "End", "Signed copy", "Owner", "Renewal"]} rows={filtered.map((agreement) => [agreement.partner, agreement.reference, <span className="pill" key="status">{agreement.status}</span>, formatDate(agreement.startDate), formatDate(agreement.endDate), agreement.signedCopy, agreement.owner, agreement.renewal])} empty="No agreements match the current filters." /></section></>;
}

function ProjectsPage() { return <div className="project-grid">{repository.projects.map((project) => { const complete = project.milestones.filter((milestone) => milestone.status === "Complete").length; return <section className="box project-card" key={project.id}><div className="card-heading"><div><h3>{project.name}</h3><p>{project.partner}</p></div><span className="pill">{project.status}</span></div><div className="project-meta"><span>Owner: {project.owner}</span><span>{formatDate(project.startDate)} – {formatDate(project.endDate)}</span></div><div className="progress"><i style={{ width: `${complete / project.milestones.length * 100}%` }} /></div><small>{complete} of {project.milestones.length} milestones complete</small><div className="milestones">{project.milestones.map((milestone) => <div className="milestone" key={milestone.id}><span>{milestone.title}</span><span className={milestone.status === "Overdue" ? "text-bordo" : ""}>{milestone.status} · {formatDate(milestone.dueDate)}</span></div>)}</div></section>; })}</div>; }

function FinancePage() { const budgetTotal = repository.budgets.reduce((sum, item) => sum + item.amount, 0); const receivedTotal = repository.fundsReceived.filter((item) => item.status === "Received").reduce((sum, item) => sum + item.amount, 0); const invoiceTotal = repository.invoices.reduce((sum, item) => sum + item.amount, 0); return <><div className="kpis"><Kpi value={budgetTotal} label="Budgeted (INR)" /><Kpi value={receivedTotal} label="Funds received (INR)" /><Kpi value={invoiceTotal} label="Invoices (INR)" /></div><div className="finance-sections"><FinanceSection title="Budgets">{repository.budgets.map((item) => <FinanceRow key={item.id} label={`${item.partner} · ${item.project}`} value={money(item.amount)} detail={item.status} />)}</FinanceSection><FinanceSection title="Funds received">{repository.fundsReceived.map((item) => <FinanceRow key={item.id} label={`${item.partner} · ${item.project}`} value={money(item.amount)} detail={`${item.status} · ${formatDate(item.receivedDate)}`} />)}</FinanceSection><FinanceSection title="Invoices"><DataTable headers={["Partner", "Invoice date", "Due date", "Amount", "Status"]} rows={repository.invoices.map((item) => [item.partner, formatDate(item.invoiceDate), item.dueDate ? formatDate(item.dueDate) : "Due date not recorded", money(item.amount), <span className="pill" key="status">{item.status}</span>])} empty="No invoices recorded." /></FinanceSection></div></>; }
function FinanceSection({ title, children }: { title: string; children: ReactNode }) { return <section className="box"><h3>{title}</h3>{children}</section>; }
function FinanceRow({ label, value, detail }: { label: string; value: string; detail: string }) { return <div className="finance-row"><span><b>{label}</b><small>{detail}</small></span><strong className="mono">{value}</strong></div>; }

function ReportsPage() { const [tab, setTab] = useState("All"); const filtered = repository.reports.filter((report) => tab === "All" || report.status === tab); return <section className="box"><div className="tabs report-tabs">{["All", "Pending", "Overdue", "Submitted"].map((item) => <button className={tab === item ? "active" : ""} key={item} onClick={() => setTab(item)}>{item}</button>)}</div><DataTable headers={["Type", "Partner", "Project", "Due", "Status", "Owner"]} rows={filtered.map((report) => [report.type, report.partner, report.project, formatDate(report.dueDate), <span className={`pill ${report.status === "Overdue" ? "high" : ""}`} key="status">{report.status}</span>, report.owner])} empty="No reports match this tab." /></section>; }

function ImportPage() {
  const [preview, setPreview] = useState<ImportPreview | null>(null); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const parse = async (file: File) => {
    setBusy(true); setPreview(null); setMessage("");
    try { const result = await api.importPreview(file, "projects"); setPreview(result); setMessage(`${result.total_rows_detected} rows previewed from ${file.name}. No records were written.`); }
    catch (err) { setMessage(err instanceof Error ? err.message : "Could not read this file."); }
    finally { setBusy(false); }
  };
  return <div className="import-flow"><label className="dropzone">{busy ? "Reading file on the server…" : "Drop a CSV or XLSX file here"}<input type="file" accept=".csv,.xlsx" onChange={(event) => { const file = event.target.files?.[0]; if (file) void parse(file); }} /></label>{message && !preview && <p className="import-message" role="alert">{message}</p>}{preview && <><section className="box"><h3>Preview · detected columns</h3><div className="mapping">{preview.headers.length ? preview.headers.map((header) => <b key={header}>{header || "(blank header)"}</b>) : <span>No header row found.</span>}</div></section><section className="box validation"><h3>Validation summary</h3><div><span className="pill">Valid · {preview.valid_count}</span><span className="pill high">Invalid · {preview.invalid_count}</span></div>{preview.issues.slice(0, 5).map((issue) => <p key={issue.row}>Row {issue.row}: {issue.issues.join("; ")}</p>)}<p>{preview.warning}</p></section><button className="btn" disabled title="Saving imported rows arrives in Step 10">Confirm import (available in Step 10)</button><p className="import-message">{message}</p></>}</div>;
}

function DataTable({ headers, rows, empty }: { headers: string[]; rows: Array<Array<ReactNode>>; empty: string }) { return rows.length ? <div className="table-wrap"><table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}</tbody></table></div> : <TableState message={empty} />; }

function Drawer({ alert, asOf, onClose, onChanged }: { alert: Alert; asOf: string; onClose: () => void; onChanged: (message: string) => void }) {
  const [ai, setAi] = useState<AnalyzeResponse | null>(null); const [running, setRunning] = useState(false);
  const [mode, setMode] = useState<"none" | "task" | "defer" | "dismiss">("none");
  const [owner, setOwner] = useState(alert.owner === "Unassigned" ? "" : alert.owner); const [due, setDue] = useState("");
  const [deferUntil, setDeferUntil] = useState(""); const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => { const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); }; window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey); }, [onClose]);
  const run = async () => {
    setRunning(true); setAi(null);
    const context = [`Alert: ${alert.ruleTitle}. ${alert.ruleDescription}`, ...alert.facts.map((fact) => `${fact.label}: ${fact.value}`), ...alert.computed.map((fact) => `${fact.label} (computed): ${fact.value}`), `Rule-based next step: ${alert.recommendation}`].join("\n");
    try { setAi(await api.analyze({ partner_id: alert.partnerId ?? undefined, context })); }
    catch (err) { setAi({ summary: err instanceof Error ? err.message : "The AI request failed.", observations: [], recommendations: [], ai_used: false, ai_error: "request_failed" }); }
    finally { setRunning(false); }
  };
  const act = async (action: () => Promise<unknown>, message: string) => {
    setBusy(true); setError("");
    try { await action(); onChanged(message); } catch (err) { setError(err instanceof Error ? err.message : "The request failed."); } finally { setBusy(false); }
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (mode === "task") { if (owner.trim().length < 2) { setError("Assign a responsible owner (at least 2 characters)."); return; } void act(() => api.alerts.createTask(alert.id, { owner: owner.trim(), due_date: due || null }), `Follow-up task created for ${owner.trim()}.`); }
    if (mode === "defer") { if (!deferUntil) { setError("Choose the date to bring this alert back."); return; } void act(() => api.alerts.review(alert.id, { decision: "deferred", deferred_until: deferUntil }), `Deferred until ${formatDate(deferUntil)}.`); }
    if (mode === "dismiss") { if (reason.trim().length < 5) { setError("Give a reason of at least 5 characters; it is recorded in the activity log."); return; } void act(() => api.alerts.review(alert.id, { decision: "dismissed", reason: reason.trim() }), "Alert dismissed. It returns if the record changes."); }
  };
  const minDefer = (() => { const d = new Date(`${asOf}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + 1); return d.toISOString().slice(0, 10); })();
  return <div className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title"><button className="close" onClick={onClose} aria-label="Close alert details">×</button><span className={`pill ${alert.priority === "High" ? "high" : "outline-pill"}`}>{alert.priority} · score {alert.score}{alert.review ? ` · ${alert.review.decision.replace("_", " ")}` : ""}</span><h2 id="drawer-title">{alert.partner}: {alert.title}</h2>
    <DrawerSection title="Verified record facts">{alert.facts.map((fact) => <div className="evidence" key={fact.label}><span className="mono">{fact.label}</span><b className="mono">{String(fact.value)}</b></div>)}<div className="evidence"><span>Owner</span><b>{alert.owner}</b></div>{alert.demo && <small>From a fictional demo record.</small>}</DrawerSection>
    {alert.computed.length > 0 && <DrawerSection title={`Computed by the rule · as of ${formatDate(asOf)}`}>{alert.computed.map((fact) => <div className="evidence" key={fact.label}><span className="mono">{fact.label}</span><b className="mono">{String(fact.value)}</b></div>)}</DrawerSection>}
    <DrawerSection title={`Rule explanation · ${alert.rule}`}><p>{alert.ruleDescription}</p><p>{alert.why}</p>{alert.factors.map((factor) => <div className="evidence" key={factor.label}><span>{factor.label}</span><b className="mono">{factor.points > 0 ? `+${factor.points}` : factor.points}</b></div>)}<small>Priority is a transparent business rule, not a prediction.</small></DrawerSection>
    <DrawerSection title="Rule-based next step"><p>{alert.recommendation}</p></DrawerSection>
    <DrawerSection title="AI assistance · generated, not verified" ai><button className="btn bordo" onClick={() => void run()} disabled={running}>{running ? "Asking Gemini…" : "Ask Gemini for a recommendation"}</button><div className="ai-output mono" aria-live="polite">{!running && !ai && "No recommendation requested."}{running && "▸ Sending this alert's facts to the backend…"}{ai && (ai.ai_used ? <span className="ai-copy">{[ai.summary, ...ai.observations, ...ai.recommendations].join("\n")}</span> : <span className="ai-copy">AI was not used ({ai.ai_error ?? "unknown reason"}). {ai.summary}</span>)}</div></DrawerSection>
    <DrawerSection title="Human decision">{error && <p className="api-state error" role="alert">{error}</p>}
      {mode === "none" && <div className="button-row"><button className="btn" disabled={busy || alert.review?.decision === "task_created"} onClick={() => setMode("task")}>Create follow-up task</button><button className="btn outline" disabled={busy || alert.review?.decision === "acknowledged"} onClick={() => void act(() => api.alerts.review(alert.id, { decision: "acknowledged" }), "Alert acknowledged.")}>Acknowledge</button><button className="btn outline" disabled={busy} onClick={() => setMode("defer")}>Defer</button><button className="btn outline" disabled={busy} onClick={() => setMode("dismiss")}>Dismiss</button>{alert.review && <button className="btn outline" disabled={busy} onClick={() => void act(() => api.alerts.clearReview(alert.id), "Review cleared; the alert is open again.")}>Reopen</button>}</div>}
      {mode !== "none" && <form className="drawer-form" onSubmit={submit} noValidate>
        {mode === "task" && <><label>Assign to<input value={owner} onChange={(event) => { setOwner(event.target.value); setError(""); }} maxLength={120} autoFocus /></label><label>Due date (optional)<input type="date" value={due} onChange={(event) => setDue(event.target.value)} /></label></>}
        {mode === "defer" && <label>Bring back on<input type="date" min={minDefer} value={deferUntil} onChange={(event) => { setDeferUntil(event.target.value); setError(""); }} autoFocus /></label>}
        {mode === "dismiss" && <label>Reason for dismissing<textarea rows={2} maxLength={500} value={reason} onChange={(event) => { setReason(event.target.value); setError(""); }} autoFocus /></label>}
        <div className="button-row"><button className="btn" type="submit" disabled={busy}>{busy ? "Saving…" : mode === "task" ? "Create task" : mode === "defer" ? "Defer alert" : "Dismiss alert"}</button><button className="btn outline" type="button" disabled={busy} onClick={() => { setMode("none"); setError(""); }}>Back</button></div>
      </form>}
    </DrawerSection></div>;
}
function DrawerSection({ title, children, ai = false }: { title: string; children: ReactNode; ai?: boolean }) { return <section className={`drawer-section${ai ? " ai" : ""}`}><h4>{title}</h4>{children}</section>; }

export default function App() {
  return <Routes><Route path="/" element={<Landing />} /><Route path="/auth" element={<Auth />} /><Route path="*" element={<AppShell />} /></Routes>;
}
