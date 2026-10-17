import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { repository, type Agreement, type Invoice, type PipelineItem, type PipelineStage, type Project, type Report } from "../data/repository";

type Alert = {
  id: string;
  rule: string;
  partner: string;
  title: string;
  priority: "High" | "Medium" | "Low";
  days: number;
  owner: string;
  evidence: [string, string][];
  why: string;
  recommendation: string;
  status: "Open" | "Resolved";
};

const dateFromToday = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
};

const initialAlerts: Alert[] = [
  { id: "A1", rule: "RPT-OVD-01", partner: "Greenleaf Skills Foundation", title: "Quarterly report 9 days overdue", priority: "High", days: -9, owner: "Anita R.", evidence: [["report.type", "Quarterly Progress"], ["report.dueDate", dateFromToday(-9)], ["report.status", "Pending"], ["submittedAt", "— (empty)"]], why: "Late reports can delay the next fund release and weaken partner trust.", recommendation: "Greenleaf’s quarterly report is overdue by 9 days. Suggest a courteous reminder to the programme lead and a firm new date. No contact attempt is recorded, so confirm no one has already reached out.", status: "Open" },
  { id: "A2", rule: "MOU-EXP-01", partner: "Kaveri Retail Academy", title: "MOU expires in 14 days, no renewal", priority: "High", days: 14, owner: "Rahul S.", evidence: [["agreement.endDate", dateFromToday(14)], ["agreement.status", "Active"], ["renewalStatus", "— (empty)"]], why: "An expired MOU leaves training activities without a signed basis.", recommendation: "The MOU ends in 14 days with no renewal recorded. Suggest scheduling a renewal call this week. Whether the partner wants to renew is unknown from the records.", status: "Open" },
  { id: "A3", rule: "UC-OVD-02", partner: "Sahyadri Agro Trust", title: "Utilization certificate 21 days overdue", priority: "High", days: -21, owner: "Meera K.", evidence: [["uc.dueDate", dateFromToday(-21)], ["uc.status", "Pending"], ["project", "Agri Skilling Cohort 3"]], why: "Pending UCs block further disbursement on funded projects.", recommendation: "UC is three weeks overdue. Suggest escalating to the finance contact and asking for an expected submission date.", status: "Open" },
  { id: "A4", rule: "MS-OVD-01", partner: "Northgate Logistics", title: "Milestone “Cohort 2 placements” past due", priority: "Medium", days: -4, owner: "Rahul S.", evidence: [["milestone.dueDate", dateFromToday(-4)], ["milestone.status", "In progress"]], why: "Placement milestones drive reporting and renewal conversations.", recommendation: "Milestone is 4 days late but still in progress. Suggest asking for a revised completion date before treating it as a risk.", status: "Open" },
  { id: "A5", rule: "MOU-DOC-01", partner: "Lotus Healthcare Skills", title: "Signed MOU copy missing", priority: "Medium", days: 0, owner: "Anita R.", evidence: [["agreement.signedCopyStatus", "Missing"], ["agreement.status", "Active"]], why: "Without the signed copy, obligations cannot be verified in audits.", recommendation: "The record shows no signed copy. This may be a data gap rather than a real absence. Suggest checking the shared drive first.", status: "Open" },
  { id: "A6", rule: "MOU-EXP-01", partner: "Brahma Textile Mills", title: "MOU expires in 27 days", priority: "Low", days: 27, owner: "Meera K.", evidence: [["agreement.endDate", dateFromToday(27)], ["renewalStatus", "In discussion"]], why: "Renewal is in discussion, so this is for visibility.", recommendation: "Renewal talks are underway. Suggest a check-in note to confirm timelines.", status: "Open" },
];

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
  const [alerts, setAlerts] = useState(initialAlerts);
  const [tasks, setTasks] = useState<string[]>([]);
  const [selected, setSelected] = useState<Alert | null>(null);
  const open = alerts.filter((alert) => alert.status === "Open");
  const sorted = useMemo(() => [...open].sort((a, b) => ({ High: 0, Medium: 1, Low: 2 }[a.priority] - ({ High: 0, Medium: 1, Low: 2 }[b.priority]) || a.days - b.days)), [open]);
  const page = location.pathname;
  const title = page === "/action-center" ? "Action Center" : page === "/partner-360" ? "Kaveri Retail Academy" : page === "/dashboard" ? "Good day, team." : page === "/pipeline" ? "Pipeline" : page === "/agreements" ? "Agreements" : page === "/projects" ? "Projects" : page === "/finance" ? "Finance" : page === "/reports" ? "Reports & UCs" : "Import";
  const eyebrow = page === "/dashboard" ? "Portfolio overview" : page === "/partner-360" ? "Partner 360" : "Synthetic demo data";
  return <div className="app-shell"><aside className="sidebar"><Logo light /><nav>{[{to:"/dashboard", label:"Dashboard"}, {to:"/action-center", label:"Action Center", count:open.length}, {to:"/partner-360", label:"Partner 360"}, {to:"/pipeline", label:"Pipeline"}, {to:"/agreements", label:"Agreements"}, {to:"/projects", label:"Projects"}, {to:"/finance", label:"Finance"}, {to:"/reports", label:"Reports & UCs"}, {to:"/import", label:"Import"}].map((item) => <NavLink key={item.to} to={item.to} className={({isActive}) => isActive ? "active" : ""}>{item.label}{item.count ? <span className="pill high">{item.count}</span> : null}</NavLink>)}</nav><button className="logout" onClick={() => navigate("/")}>↩ Log out</button><small>Synthetic demo data</small></aside><main className="app-main"><div className="page-header"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1></div>{page === "/dashboard" && <Dashboard open={open} sorted={sorted} tasks={tasks} onSelect={setSelected} />}{page === "/action-center" && <ActionCenter open={open} sorted={sorted} tasks={tasks} onSelect={setSelected} />}{page === "/partner-360" && <Partner360 open={open} onSelect={setSelected} />}{page === "/pipeline" && <PipelinePage />}{page === "/agreements" && <AgreementsPage />}{page === "/projects" && <ProjectsPage />}{page === "/finance" && <FinancePage />}{page === "/reports" && <ReportsPage />}{page === "/import" && <ImportPage />}</main>{selected && <Drawer alert={selected} onClose={() => setSelected(null)} onResolve={() => { setAlerts((items) => items.map((item) => item.id === selected.id ? { ...item, status: "Resolved" } : item)); setTasks((items) => [...items, `${selected.partner}: ${selected.title}`]); setSelected(null); }} />}</div>;
}

function AlertRow({ alert, index, onSelect }: { alert: Alert; index: number; onSelect: (alert: Alert) => void }) {
  return <button className="alert-row" onClick={() => onSelect(alert)}><strong>{index + 1}</strong><span className="alert-copy"><b>{alert.partner}</b><small>{alert.title} · {alert.owner}</small></span><span className={`pill ${alert.priority === "High" ? "high" : "outline-pill"}`}>{alert.priority}</span><span className="pill outline-pill">{alert.days < 0 ? `${Math.abs(alert.days)}d overdue` : alert.days === 0 ? "Today" : `in ${alert.days}d`}</span></button>;
}

function Dashboard({ open, sorted, tasks, onSelect }: { open: Alert[]; sorted: Alert[]; tasks: string[]; onSelect: (alert: Alert) => void }) {
  const overdue = open.filter((alert) => alert.days < 0).length;
  const expiring = open.filter((alert) => alert.rule === "MOU-EXP-01" && alert.days <= 30).length;
  const families = Object.entries(open.reduce<Record<string, number>>((result, alert) => { const key = alert.rule.split("-")[0]; result[key] = (result[key] || 0) + 1; return result; }, {}));
  const max = Math.max(1, ...families.map(([, count]) => count));
  return <><div className="kpis"><Kpi value={open.length} label="Open alerts" /><Kpi value={overdue} label="Overdue items" hot /><Kpi value={expiring} label="MOUs expiring ≤30d" /><Kpi value={tasks.length} label="Follow-ups created" /></div><div className="grid2"><section className="box"><h3>Today’s 5</h3>{sorted.slice(0, 5).map((alert, index) => <AlertRow key={alert.id} alert={alert} index={index} onSelect={onSelect} />)}{!sorted.length && <p>All clear. Obligations: got them.</p>}</section><section className="box"><h3>Alerts by rule family</h3>{families.map(([name, count]) => <div className="bar-row" key={name}><span>{name}</span><i style={{ width: `${count / max * 55}%` }} /><b>{count}</b></div>)}</section></div></>;
}

function Kpi({ value, label, hot = false }: { value: number; label: string; hot?: boolean }) { return <div className={`kpi ${hot ? "hot" : ""}`}><b>{value}</b><span>{label}</span></div>; }
function ActionCenter({ open, sorted, tasks, onSelect }: { open: Alert[]; sorted: Alert[]; tasks: string[]; onSelect: (alert: Alert) => void }) { return <><section className="box"><h3>All outstanding ({open.length})</h3>{sorted.map((alert, index) => <AlertRow key={alert.id} alert={alert} index={index} onSelect={onSelect} />)}</section><section className="box task-box"><h3>Follow-up tasks</h3>{tasks.map((task) => <div className="task-row" key={task}><span>{task}</span><span className="pill">Assigned</span></div>)}{!tasks.length && <small>None yet. Approve a recommendation to create one.</small>}</section></>; }
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

function countCsvDataRows(contents: string): number {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < contents.length; index += 1) {
    const character = contents[index];
    if (quoted) {
      if (character === '"' && contents[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"' && field.length === 0) {
      quoted = true;
    } else if (character === ",") {
      row.push(field);
      field = "";
    } else if (character === "\r" || character === "\n") {
      row.push(field);
      if (row.some((value) => value.trim())) rows.push(row);
      row = [];
      field = "";
      if (character === "\r" && contents[index + 1] === "\n") index += 1;
    } else {
      field += character;
    }
  }

  if (quoted) throw new Error("The CSV contains an unclosed quoted field.");
  row.push(field);
  if (row.some((value) => value.trim())) rows.push(row);
  if (rows.length === 0 || !rows[0].some((value) => value.trim())) {
    throw new Error("The CSV must include a header row.");
  }
  return rows.length - 1;
}

function ImportPage() {
  const [preview, setPreview] = useState(false); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  const parse = async (file: File) => {
    setPreview(false);
    setMessage("");
    setError("");
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Only CSV files are supported by this preview.");
      return;
    }
    try {
      const rows = countCsvDataRows(await file.text());
      setPreview(true);
      setMessage(`${rows} rows previewed from ${file.name}. No records were written.`);
    } catch (parseError) {
      setError(parseError instanceof Error ? parseError.message : "Unable to read this CSV file.");
    }
  };
  return <div className="import-flow"><label className="dropzone">Choose a CSV file to preview<input type="file" accept=".csv,text/csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void parse(file); }} /></label>{error && <p className="import-message" role="alert">{error}</p>}{preview && <><section className="box"><h3>Preview · column mapping</h3><div className="mapping"><span>partner</span><b>Partner Name</b><span>project</span><b>Project Name</b><span>due_date</span><b>Due Date</b></div></section><section className="box validation"><h3>Validation summary</h3><div><span className="pill">Valid · 0</span><span className="pill outline-pill">Warnings · 0</span><span className="pill high">Invalid · 0</span></div><p>Duplicate warnings will appear here before confirmation.</p></section><button className="btn" disabled={!preview} onClick={() => setMessage("Import confirmed for the previewed rows.")}>Confirm import</button><p className="import-message">{message}</p></>}</div>;
}

function DataTable({ headers, rows, empty }: { headers: string[]; rows: Array<Array<ReactNode>>; empty: string }) { return rows.length ? <div className="table-wrap"><table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}</tbody></table></div> : <TableState message={empty} />; }

function Drawer({ alert, onClose, onResolve }: { alert: Alert; onClose: () => void; onResolve: () => void }) {
  const [running, setRunning] = useState(false); const [finished, setFinished] = useState(false);
  const run = () => { setRunning(true); window.setTimeout(() => { setFinished(true); }, 2200); };
  return <div className="drawer"><button className="close" onClick={onClose}>×</button><span className={`pill ${alert.priority === "High" ? "high" : "outline-pill"}`}>{alert.priority} · {alert.status}</span><h2>{alert.partner}: {alert.title}</h2><DrawerSection title="Verified record facts">{alert.evidence.map(([key, value]) => <div className="evidence" key={key}><span className="mono">{key}</span><b className="mono">{value}</b></div>)}<div className="evidence"><span>Owner</span><b>{alert.owner}</b></div></DrawerSection><DrawerSection title={`Rule explanation · ${alert.rule}`}><p>{alert.why}</p></DrawerSection><DrawerSection title="AI assistance · generated, not verified" ai><button className="btn bordo" onClick={run}>Ask Gemini for a recommendation</button><div className="ai-output mono">{!running && "No recommendation requested."}{running && !finished && "▸ Reading linked fields…\n▸ Checking for contact history…\n▸ Drafting suggestion…"}{finished && <span className="ai-copy">{alert.recommendation}</span>}</div></DrawerSection><DrawerSection title="Human decision"><div className="button-row"><button className="btn" disabled={!finished} onClick={onResolve}>Approve & create task</button><button className="btn outline" onClick={onClose}>Defer</button></div></DrawerSection></div>;
}
function DrawerSection({ title, children, ai = false }: { title: string; children: ReactNode; ai?: boolean }) { return <section className={`drawer-section${ai ? " ai" : ""}`}><h4>{title}</h4>{children}</section>; }

export default function App() {
  return <Routes><Route path="/" element={<Landing />} /><Route path="/auth" element={<Auth />} /><Route path="*" element={<AppShell />} /></Routes>;
}
