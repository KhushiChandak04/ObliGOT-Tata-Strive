import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import Dialog from "../components/ui/Dialog";
import AgreementForm from "../features/agreements/AgreementForm";
import PartnerForm from "../features/partners/PartnerForm";
import OpportunityForm from "../features/pipeline/OpportunityForm";
import MilestoneForm from "../features/projects/MilestoneForm";
import ProjectForm from "../features/projects/ProjectForm";
import {
  AGREEMENT_STATUSES,
  RENEWAL,
  SIGNED_COPY,
  isWebLink,
  labelOf,
} from "../lib/agreements";
import { STAGES, nextStage, stageLabel } from "../lib/pipeline";
import { MILESTONE_STATUSES } from "../lib/projects";
import { api } from "../services/functions.service";
import { useResource } from "../lib/useResource";
import { CATEGORY_LABELS, todaysAlerts } from "../lib/alerts";
import {
  createUserWithEmailAndPassword,
  getRedirectResult,
  signInWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  signOut,
  updateProfile,
} from "firebase/auth";
import { firebaseAuth, googleProvider } from "../lib/firebase";
import { RequireAuth, authErrorMessage, useAuthUser } from "../lib/auth";
import type {
  ActionItem,
  Agreement,
  Alert as ApiAlert,
  AlertEvidence,
  AlertsResponse,
  AnalyzeResponse,
  ClauseProposal,
  DocumentEvidence,
  DocumentReview,
  FinanceRecord,
  FinancialTermProposal,
  ImportPreview,
  Milestone,
  ObligationProposal,
  Opportunity,
  Partner,
  Project,
  ProposalCollection,
  ScopeProposal,
  SourceDocument,
  TableProposal,
} from "../types";

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

const toViewAlert = (
  alert: ApiAlert,
  partnerName: (id: string) => string | undefined,
): Alert => ({
  id: alert.id,
  rule: alert.rule_id,
  ruleTitle: alert.rule_title,
  ruleDescription: alert.rule_description,
  partnerId: alert.partner_id ?? null,
  partner: alert.partner_id
    ? (partnerName(alert.partner_id) ?? alert.partner_id)
    : "No partner linked",
  title: `${alert.rule_title}: ${alert.record_title}`,
  priority:
    alert.priority.level === "high"
      ? "High"
      : alert.priority.level === "medium"
        ? "Medium"
        : "Low",
  score: alert.priority.score,
  factors: alert.priority.factors,
  days: alert.days_remaining ?? null,
  owner: alert.owner,
  category: CATEGORY_LABELS[alert.category] ?? alert.category,
  facts: alert.evidence.filter((e) => e.source === "record"),
  computed: alert.evidence.filter((e) => e.source === "computed"),
  why: alert.why_it_matters,
  recommendation: alert.recommended_action,
  review: alert.review,
  demo: alert.source_label === "demo",
});

/** Short timing label from the backend's days_remaining; the browser does no deadline arithmetic. */
const timing = (alert: Alert) =>
  alert.days === null
    ? "No date"
    : alert.days < 0
      ? `${Math.abs(alert.days)}d overdue`
      : alert.days === 0
        ? "Today"
        : `in ${alert.days}d`;
const isOpenTask = (task: ActionItem) =>
  task.status === "open" || task.status === "in_review";

function Logo({ light = false }: { light?: boolean }) {
  return (
    <span className={`logo${light ? " light" : ""}`}>
      Obli<i>GOT</i>
    </span>
  );
}

function Landing() {
  const navigate = useNavigate();
  const [trace, setTrace] = useState(0);
  const lines = [
    "▸ Evaluating 214 stored records…",
    "✓ Rule MOU-EXP-01 fired",
    "  agreement.endDate = today+14d ISO",
    "  renewalStatus = (empty)",
    "⚠ Rule RPT-OVD-01 fired",
    "✓ Priority: HIGH (deterministic)",
    "▸ Gemini drafting follow-up…",
    "⏸ Waiting for human approval",
  ];
  useEffect(() => {
    const timer = window.setInterval(
      () => setTrace((value) => (value >= lines.length ? 0 : value + 1)),
      750,
    );
    return () => window.clearInterval(timer);
  }, [lines.length]);
  return (
    <div className="landing">
      <nav className="top-nav">
        <Logo />
        <div className="nav-actions">
          <a href="#how">How it works</a>
          <a href="#why">Why ObliGOT</a>
          <button className="btn outline" onClick={() => navigate("/auth")}>
            Sign in
          </button>
          <button className="btn" onClick={() => navigate("/auth?mode=up")}>
            Get started
          </button>
        </div>
      </nav>
      <section className="hero">
        <div>
          <span className="eyebrow">
            Partnership intelligence · Tata STRIVE
          </span>
          <h1>
            Obligations?{" "}
            <span className="got">
              Got them.<b>GOT IT ✓</b>
            </span>
          </h1>
          <p className="lead">
            MOUs, reports, invoices and UCs live in a dozen trackers. ObliGOT
            watches them all, explains what needs attention, and drafts the next
            move. Your team approves it.
          </p>
          <div className="button-row">
            <button className="btn" onClick={() => navigate("/auth")}>
              Open the workspace →
            </button>
            <a className="btn outline" href="#how">
              See the agent think
            </a>
          </div>
        </div>
        <div className="agent">
          <div className="agent-bar">
            <span>● ● ●</span>
            <b>obligot-agent · live trace</b>
          </div>
          <div className="trace mono">
            {lines.slice(0, trace).map((line, index) => (
              <div
                key={line}
                className={
                  index === 1 || index === 5
                    ? "ok"
                    : index === 4
                      ? "warning"
                      : ""
                }
              >
                {line}
                {index === lines.length - 1 && trace === lines.length ? (
                  <em className="cursor" />
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </section>
      <div className="marquee">
        <div>
          MOU expiring ✦ Report overdue ✦ UC pending ✦ Invoice aging ✦ Milestone
          slipped ✦ Renewal due ✦ MOU expiring ✦ Report overdue ✦ UC pending ✦
          Invoice aging ✦ Milestone slipped ✦ Renewal due ✦
        </div>
      </div>
      <section className="section" id="how">
        <h2>Every alert answers five questions</h2>
        <div className="flow">
          {[
            ["Issue", "What was flagged by a rule"],
            ["Evidence", "The exact fields and dates"],
            ["Why it matters", "Plain-language impact"],
            ["Next action", "AI suggests, you decide"],
            ["Owner + due", "Tracked until resolved"],
          ].map(([title, detail], index) => (
            <div className="step" key={title}>
              <b>0{index + 1}</b>
              {title}
              <small>{detail}</small>
            </div>
          ))}
        </div>
      </section>
      <section className="section why" id="why">
        <div className="three">
          <InfoPanel
            className="green-panel"
            tag="DETERMINISTIC"
            title="Rules decide facts"
          >
            Dates, deadlines and amounts are computed by code, never guessed by
            a model.
          </InfoPanel>
          <InfoPanel
            className="card-panel"
            tag="GEMINI"
            title="AI explains & drafts"
          >
            Summaries and follow-ups, clearly labelled as AI interpretation with
            uncertainty shown.
          </InfoPanel>
          <InfoPanel
            className="bordo-panel"
            tag="HUMAN-IN-THE-LOOP"
            title="You approve"
          >
            Nothing happens until a person reviews it. Every decision lands in
            the audit trail.
          </InfoPanel>
        </div>
      </section>
      <footer>
        <Logo light />
        <span className="mono">
          Built for Tata STRIVE Code Odyssey 5.0 · Demo uses synthetic data
        </span>
      </footer>
    </div>
  );
}

function InfoPanel({
  className = "",
  tag,
  title,
  children,
}: {
  className?: string;
  tag: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className={`info-panel ${className}`}>
      <span className="tag">{tag}</span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

function Auth() {
  const navigate = useNavigate();
  const search = new URLSearchParams(useLocation().search);
  const mode = search.get("mode") === "up";
  // Only same-app paths are accepted as a return target (no open redirects).
  const nextParam = search.get("next") ?? "";
  const next =
    nextParam.startsWith("/") && !nextParam.startsWith("//")
      ? nextParam
      : "/dashboard";
  const [signup, setSignup] = useState(mode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleError, setGoogleError] = useState("");
  const [formError, setFormError] = useState("");
  useEffect(() => {
    if (!firebaseAuth) return;
    void getRedirectResult(firebaseAuth)
      .then((result) => {
        if (result) navigate(next, { replace: true });
      })
      .catch((error) => setGoogleError(authErrorMessage(error)));
  }, [navigate, next]);
  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setFormError("");
    if (!firebaseAuth) {
      setFormError(
        "Firebase is not configured for this build (frontend/.env).",
      );
      return;
    }
    setBusy(true);
    try {
      if (signup) {
        const created = await createUserWithEmailAndPassword(
          firebaseAuth,
          email.trim(),
          password,
        );
        if (name.trim())
          await updateProfile(created.user, { displayName: name.trim() });
      } else {
        await signInWithEmailAndPassword(firebaseAuth, email.trim(), password);
      }
      navigate(next, { replace: true });
    } catch (error) {
      setFormError(authErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }
  async function continueWithGoogle(): Promise<void> {
    if (!firebaseAuth) {
      setGoogleError(
        "Firebase is not configured for this build (frontend/.env).",
      );
      return;
    }
    setGoogleLoading(true);
    setGoogleError("");
    try {
      await signInWithPopup(firebaseAuth, googleProvider);
      navigate(next, { replace: true });
    } catch (error) {
      const code =
        error && typeof error === "object" && "code" in error
          ? String(error.code)
          : "";
      if (code === "auth/popup-closed-by-user") return;
      if (code === "auth/popup-blocked") {
        try {
          await signInWithRedirect(firebaseAuth, googleProvider);
        } catch (redirectError) {
          setGoogleError(authErrorMessage(redirectError));
        }
        return;
      }
      setGoogleError(authErrorMessage(error));
    } finally {
      setGoogleLoading(false);
    }
  }
  return (
    <div className="auth-page">
      <div className="auth-left">
        <Link to="/">
          <Logo light />
        </Link>
        <h2>From commitments to accountability.</h2>
        <span className="mono">Secured with Firebase Authentication.</span>
      </div>
      <div className="auth-right">
        <form className="auth-form" onSubmit={(event) => void submit(event)}>
          <h2>{signup ? "Join the team" : "Welcome back"}</h2>
          <p>Sign in to your partnership workspace.</p>
          <div className="tabs">
            <button
              type="button"
              className={!signup ? "active" : ""}
              onClick={() => {
                setSignup(false);
                setFormError("");
              }}
            >
              Sign in
            </button>
            <button
              type="button"
              className={signup ? "active" : ""}
              onClick={() => {
                setSignup(true);
                setFormError("");
              }}
            >
              Sign up
            </button>
          </div>
          {signup && (
            <label>
              Full name
              <input
                placeholder="Your name"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}
          <label>
            Work email
            <input
              type="email"
              placeholder="you@tatastrive.org"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              placeholder="••••••••"
              autoComplete={signup ? "new-password" : "current-password"}
              minLength={signup ? 6 : undefined}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button className="btn submit" type="submit" disabled={busy}>
            {busy ? "Please wait…" : signup ? "Create account" : "Sign in"}
          </button>
          {formError && (
            <div
              role="alert"
              style={{
                color: "var(--bordo)",
                font: "13px 'DM Sans', sans-serif",
                marginTop: 8,
              }}
            >
              {formError}
            </div>
          )}
          <div style={{ marginTop: 16 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                color: "var(--muted)",
                fontSize: 13,
              }}
            >
              <span
                style={{ height: 1.5, flex: 1, background: "var(--line)" }}
              />
              or
              <span
                style={{ height: 1.5, flex: 1, background: "var(--line)" }}
              />
            </div>
            <button
              className="btn outline"
              type="button"
              disabled={googleLoading}
              onClick={() => void continueWithGoogle()}
              style={{ width: "100%", marginTop: 12, gap: 10 }}
            >
              <svg
                aria-hidden="true"
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
              >
                <path
                  d="M9 3.5c1.45 0 2.43.63 2.99 1.16l2.18-2.13C12.84 1.2 11.14.5 9 .5 5.9.5 3.22 2.28 1.91 4.86l2.51 1.95C5.05 5.15 6.84 3.5 9 3.5Z"
                  fill="currentColor"
                />
                <path
                  d="M17.5 9.18c0-.61-.05-1.06-.16-1.53H9v2.9h4.88c-.1.72-.75 1.8-2.16 2.53l2.64 2.05c1.54-1.42 3.14-3.55 3.14-5.95Z"
                  fill="currentColor"
                />
                <path
                  d="M4.42 10.81A5.5 5.5 0 0 1 4.12 9c0-.63.11-1.24.3-1.81L1.91 5.24A8.5 8.5 0 0 0 .5 9c0 1.35.32 2.63.89 3.76l3.03-1.95Z"
                  fill="currentColor"
                />
                <path
                  d="M9 17.5c2.43 0 4.47-.8 5.96-2.17l-2.64-2.05c-.71.5-1.67.85-3.32.85-2.16 0-3.95-1.65-4.58-3.31l-3.03 1.95C2.7 15.72 5.9 17.5 9 17.5Z"
                  fill="currentColor"
                />
              </svg>
              {googleLoading ? "Connecting…" : "Continue with Google"}
            </button>
            {googleError && (
              <div
                role="alert"
                style={{
                  color: "var(--bordo)",
                  font: "13px 'DM Sans', sans-serif",
                  marginTop: 8,
                }}
              >
                {googleError}
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthUser();
  const logOut = async () => {
    if (firebaseAuth) await signOut(firebaseAuth);
    navigate("/");
  };
  const workspace = useResource(async () => {
    const [alerts, tasks, partners, documents] = await Promise.all([
      api.alerts.list(),
      api.actions.list(),
      api.partners.list(),
      api.documents.list(),
    ]);
    return { alerts, tasks, partners, documents };
  }, []);
  // Live records only. While loading or when the API fails, pages show loading/error states — never sample data.
  const live = workspace.data;
  const livePartners = live?.partners ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [params] = useSearchParams();
  const names = new Map(livePartners.map((p) => [p.id, p.name]));
  const apiAlerts = live?.alerts.alerts ?? [];
  const sorted = apiAlerts.map((alert) =>
    toViewAlert(alert, (id) => names.get(id)),
  ); // already ordered by priority score
  const today = todaysAlerts(apiAlerts).map((alert) =>
    toViewAlert(alert, (id) => names.get(id)),
  );
  const open = sorted;
  const tasks = (live?.tasks ?? []).filter(isOpenTask);
  const selected = sorted.find((alert) => alert.id === selectedId) ?? null;
  const select = (alert: Alert) => {
    setNotice("");
    setSelectedId(alert.id);
  };
  const changed = (message: string) => {
    setSelectedId(null);
    setNotice(message);
    workspace.reload();
  };
  const page = location.pathname;
  const title = page.startsWith("/documents/")
    ? "Document review"
    : page === "/documents"
      ? "Documents"
      : page === "/action-center"
        ? "Action Center"
        : page === "/partner-360"
          ? (names.get(params.get("id") ?? "") ??
            livePartners[0]?.name ??
            "Partner 360")
          : page === "/dashboard"
            ? "Good day, team."
            : page === "/pipeline"
              ? "Pipeline"
              : page === "/agreements"
                ? "Agreements"
                : page === "/projects"
                  ? "Projects"
                  : page === "/finance"
                    ? "Finance"
                    : page === "/reports"
                      ? "Reports & UCs"
                      : "Import";
  const eyebrow =
    page === "/dashboard"
      ? `Portfolio overview${workspace.data ? ` · rules evaluated ${formatDate(workspace.data.alerts.as_of)}` : ""}`
      : page === "/documents" || page.startsWith("/documents/")
        ? "MOU and addendum intake"
        : page === "/partner-360"
          ? "Partner 360"
          : page === "/action-center"
            ? "Live rule alerts"
            : ["/pipeline", "/agreements", "/projects"].includes(page)
              ? "Live records"
              : "Synthetic demo data";
  const usesApi = page === "/dashboard" || page === "/action-center";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Logo light />
        <nav>
          {[
            { to: "/dashboard", label: "Dashboard" },
            { to: "/documents", label: "Documents" },
            {
              to: "/action-center",
              label: "Action Center",
              count: open.length,
            },
            { to: "/partner-360", label: "Partner 360" },
            { to: "/pipeline", label: "Pipeline" },
            { to: "/agreements", label: "Agreements" },
            { to: "/projects", label: "Projects" },
            { to: "/finance", label: "Finance" },
            { to: "/reports", label: "Reports & UCs" },
            { to: "/import", label: "Import" },
          ].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {item.label}
              {item.count ? (
                <span className="pill high">{item.count}</span>
              ) : null}
            </NavLink>
          ))}
        </nav>
        {user && (
          <small title={user.email ?? ""}>
            Signed in as {user.displayName || user.email}
          </small>
        )}
        <button className="logout" onClick={() => void logOut()}>
          ↩ Log out
        </button>
        <small>
          {workspace.data?.alerts.alerts.some(
            (alert) => alert.source_label === "demo",
          )
            ? "Fictional demo records"
            : "Synthetic demo data"}
        </small>
      </aside>
      <main className="app-main">
        <div className="page-header">
          <span className="eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
        </div>
        {usesApi && workspace.error && (
          <div className="api-state error" role="alert">
            <b>Could not reach the ObliGOT API.</b>
            <span>{workspace.error.message}</span>
            <button className="btn small-btn" onClick={workspace.reload}>
              Retry
            </button>
          </div>
        )}
        {usesApi && workspace.loading && !workspace.data && (
          <p className="api-state" role="status">
            Evaluating rules on stored records…
          </p>
        )}
        {usesApi && notice && (
          <p className="api-state success" role="status">
            {notice}
          </p>
        )}
        {page === "/dashboard" && live && (
          <Dashboard
            open={open}
            sorted={today}
            tasks={tasks}
            onSelect={select}
            documents={live.documents}
          />
        )}
        {page === "/action-center" && live && (
          <ActionCenter
            open={open}
            sorted={sorted}
            tasks={tasks}
            hidden={live.alerts.counts.hidden_by_review}
            onSelect={select}
            onChanged={changed}
          />
        )}
        {page === "/partner-360" && live && (
          <Partner360
            partners={live.partners}
            open={open}
            onSelect={select}
            onChanged={workspace.reload}
          />
        )}
        {page === "/documents" && (
          <DocumentsPage partners={livePartners} />
        )}
        {page.startsWith("/documents/") && (
          <DocumentReviewPage partners={livePartners} onApproved={workspace.reload} />
        )}
        {page === "/pipeline" && <PipelinePage onChanged={workspace.reload} />}
        {page === "/agreements" && (
          <AgreementsPage onChanged={workspace.reload} />
        )}
        {page === "/projects" && <ProjectsPage onChanged={workspace.reload} />}
        {page === "/finance" && <FinancePage />}
        {page === "/reports" && <ReportsPage />}
        {page === "/import" && <ImportPage />}
      </main>
      {selected && live && (
        <Drawer
          alert={selected}
          asOf={live.alerts.as_of}
          onClose={() => setSelectedId(null)}
          onChanged={changed}
        />
      )}
    </div>
  );
}

function AlertRow({
  alert,
  index,
  onSelect,
}: {
  alert: Alert;
  index: number;
  onSelect: (alert: Alert) => void;
}) {
  return (
    <button
      className="alert-row"
      onClick={() => onSelect(alert)}
      aria-label={`${alert.partner}: ${alert.title}. ${alert.priority} priority. Open details`}
    >
      <strong>{index + 1}</strong>
      <span className="alert-copy">
        <b>{alert.partner}</b>
        <small>
          {alert.title} · {alert.owner}
          {alert.review ? ` · ${alert.review.decision.replace("_", " ")}` : ""}
        </small>
      </span>
      <span
        className={`pill ${alert.priority === "High" ? "high" : "outline-pill"}`}
      >
        {alert.priority}
      </span>
      <span className="pill outline-pill">{timing(alert)}</span>
    </button>
  );
}

function Dashboard({
  open,
  sorted,
  tasks,
  onSelect,
  documents,
}: {
  open: Alert[];
  sorted: Alert[];
  tasks: ActionItem[];
  onSelect: (alert: Alert) => void;
  documents: SourceDocument[];
}) {
  const overdue = open.filter(
    (alert) => alert.days !== null && alert.days < 0,
  ).length;
  const expiring = open.filter(
    (alert) =>
      alert.rule === "MOU_EXPIRING" && alert.days !== null && alert.days <= 30,
  ).length;
  const followUps = tasks.filter((task) => task.source_alert_id).length;
  const families = Object.entries(
    open.reduce<Record<string, number>>((result, alert) => {
      result[alert.category] = (result[alert.category] || 0) + 1;
      return result;
    }, {}),
  );
  const max = Math.max(1, ...families.map(([, count]) => count));
  return (
    <>
      <div className="kpis">
        <Kpi value={open.length} label="Open alerts" />
        <Kpi value={overdue} label="Overdue items" hot />
        <Kpi value={expiring} label="MOUs expiring ≤30d" />
        <Kpi value={followUps} label="Open follow-ups from alerts" />
      </div>
      <div className="document-strip">
        <span>
          <b>{documents.filter((d) => d.status === "needs_review").length}</b> Documents
          awaiting review
        </span>
        <span>
          <b>{documents.filter((d) => d.status === "failed" || d.status === "blocked").length}</b> Extraction
          failures / OCR
        </span>
        <span>
          <b>{documents.filter((d) => d.kind === "addendum" && d.status === "needs_review").length}</b> Pending
          addendum approvals
        </span>
      </div>
      <div className="grid2">
        <section className="box">
          <h3>Today’s 5</h3>
          {sorted.map((alert, index) => (
            <AlertRow
              key={alert.id}
              alert={alert}
              index={index}
              onSelect={onSelect}
            />
          ))}
          {!sorted.length && (
            <p>
              All clear. Every open alert already has a follow-up, or no record
              triggers a rule.
            </p>
          )}
        </section>
        <section className="box">
          <h3>Alerts by category</h3>
          {families.map(([name, count]) => (
            <div className="bar-row" key={name}>
              <span>{name}</span>
              <i style={{ width: `${(count / max) * 55}%` }} />
              <b>{count}</b>
            </div>
          ))}
          {!families.length && <p>No open alerts.</p>}
        </section>
      </div>
    </>
  );
}

function Kpi({
  value,
  label,
  hot = false,
}: {
  value: number;
  label: string;
  hot?: boolean;
}) {
  return (
    <div className={`kpi ${hot ? "hot" : ""}`}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}
function ActionCenter({
  open,
  sorted,
  tasks,
  hidden,
  onSelect,
  onChanged,
}: {
  open: Alert[];
  sorted: Alert[];
  tasks: ActionItem[];
  hidden: number;
  onSelect: (alert: Alert) => void;
  onChanged: (message: string) => void;
}) {
  const [error, setError] = useState("");
  const done = async (task: ActionItem) => {
    setError("");
    if (task.source_label === "demo") {
      setError(
        "Synthetic demo task only. Connect the backend to update this task.",
      );
      return;
    }
    try {
      await api.actions.update(task.id, { status: "done" });
      onChanged(
        `Marked “${task.title}” done. The alert clears when the underlying record is updated.`,
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update the task.",
      );
    }
  };
  return (
    <>
      <section className="box">
        <h3>All outstanding ({open.length})</h3>
        {hidden > 0 && (
          <small>
            {hidden} deferred or dismissed alert{hidden === 1 ? " is" : "s are"}{" "}
            hidden until the date passes or the record changes.
          </small>
        )}
        {sorted.map((alert, index) => (
          <AlertRow
            key={alert.id}
            alert={alert}
            index={index}
            onSelect={onSelect}
          />
        ))}
        {!sorted.length && <p>No open alerts.</p>}
      </section>
      <section className="box task-box">
        <h3>Follow-up tasks</h3>
        {error && (
          <p className="api-state error" role="alert">
            {error}
          </p>
        )}
        {tasks.map((task) => (
          <div className="task-row" key={task.id}>
            <span>
              {task.title}
              <small>
                {" "}
                · {task.owner ?? "Unassigned"}
                {task.due_date ? ` · due ${formatDate(task.due_date)}` : ""}
              </small>
            </span>
            <button
              className="btn small-btn"
              onClick={() => void done(task)}
              aria-label={`Mark ${task.title} done`}
            >
              Mark done
            </button>
          </div>
        ))}
        {!tasks.length && <small>None yet. Create one from an alert.</small>}
      </section>
    </>
  );
}
/** Partner 360: profile, MOU timeline, open alerts, linked record counts, and activity for one partner. */
function Partner360({
  partners,
  open,
  onSelect,
  onChanged,
}: {
  partners: Partner[];
  open: Alert[];
  onSelect: (alert: Alert) => void;
  onChanged: () => void;
}) {
  const [params, setParams] = useSearchParams();
  const partnerId = params.get("id") ?? partners[0]?.id ?? "";
  const [editing, setEditing] = useState(false);
  const data = useResource(async () => {
    if (!partnerId) return null;
    const [
      partner,
      agreements,
      projects,
      milestones,
      finance,
      reports,
      opportunities,
      activities,
      alerts,
    ] = await Promise.all([
      api.partners.get(partnerId),
      api.agreements.list(partnerId),
      api.projects.list(partnerId),
      api.milestones.list({ partnerId }),
      api.finance.list(partnerId),
      api.reports.list(partnerId),
      api.opportunities.list(partnerId),
      api.activities.list({ partnerId, limit: 6 }),
      api.alerts.list({ partnerId }),
    ]);
    return {
      partner,
      agreements,
      projects,
      milestones,
      finance,
      reports,
      opportunities,
      activities,
      asOf: alerts.as_of,
    };
  }, [partnerId]);
  if (!partners.length)
    return (
      <section className="box">
        <h3>No partners yet</h3>
        <p>Partner records added through the API appear here.</p>
      </section>
    );
  const d = data.data;
  // The MOU shown on the timeline: the active agreement with the nearest expiry, else the most recent one with dates.
  const mou = d
    ? [...d.agreements]
        .filter((a) => a.start_date && a.expiry_date)
        .sort(
          (a, b) =>
            Number(b.status === "active") - Number(a.status === "active") ||
            (a.expiry_date ?? "").localeCompare(b.expiry_date ?? ""),
        )[0]
    : undefined;
  const elapsed =
    mou && d
      ? Math.min(
          100,
          Math.max(
            0,
            ((Date.parse(d.asOf) - Date.parse(mou.start_date!)) /
              (Date.parse(mou.expiry_date!) - Date.parse(mou.start_date!))) *
              100,
          ),
        )
      : 0;
  const partnerAlerts = open.filter((alert) => alert.partnerId === partnerId);
  const done = d
    ? d.milestones.filter((m) => m.status === "completed").length
    : 0;
  return (
    <>
      <div className="toolbar">
        <select
          value={partnerId}
          onChange={(event) => setParams({ id: event.target.value })}
          aria-label="Choose partner"
        >
          {partners.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        {d && (
          <button className="btn small-btn" onClick={() => setEditing(true)}>
            Edit partner
          </button>
        )}
      </div>
      {data.error && (
        <div className="api-state error" role="alert">
          <b>Could not load this partner.</b>
          <span>{data.error.message}</span>
          <button className="btn small-btn" onClick={data.reload}>
            Retry
          </button>
        </div>
      )}
      {data.loading && !d && (
        <p className="api-state" role="status">
          Loading partner records…
        </p>
      )}
      {d && (
        <div className="grid2">
          <section className="box">
            <h3>Profile</h3>
            <div className="detail-row">
              <span>Category</span>
              <span>{d.partner.category}</span>
            </div>
            <div className="detail-row">
              <span>Relationship status</span>
              <span>{d.partner.status.replace("_", " ")}</span>
            </div>
            <div className="detail-row">
              <span>Owner</span>
              <span>{d.partner.owner}</span>
            </div>
            <div className="detail-row">
              <span>Contact</span>
              <span>
                {d.partner.contact_name || "Not recorded"}
                {d.partner.contact_email ? ` · ${d.partner.contact_email}` : ""}
              </span>
            </div>
            <p>{d.partner.summary || "No summary recorded."}</p>
            {d.partner.source_label === "demo" && (
              <small>Fictional demo record.</small>
            )}
          </section>
          <section className="box">
            <h3>MOU timeline</h3>
            {mou ? (
              <>
                <div
                  className="timeline"
                  role="img"
                  aria-label={`${Math.round(elapsed)}% of the agreement term elapsed`}
                >
                  <i style={{ right: `${100 - elapsed}%` }} />
                  <em style={{ right: `calc(${100 - elapsed}% - 11px)` }} />
                </div>
                <div className="detail-row">
                  <span>Agreement</span>
                  <span>{mou.title}</span>
                </div>
                <div className="detail-row">
                  <span>Start</span>
                  <span>{formatDate(mou.start_date ?? null)}</span>
                </div>
                <div className="detail-row">
                  <span>End</span>
                  <span>{formatDate(mou.expiry_date ?? null)}</span>
                </div>
                <div className="detail-row">
                  <span>Renewal</span>
                  <span>{labelOf(RENEWAL, mou.renewal_status)}</span>
                </div>
                <div className="detail-row">
                  <span>Signed copy</span>
                  <span>{labelOf(SIGNED_COPY, mou.signed_copy)}</span>
                </div>
              </>
            ) : (
              <p>
                No agreement with start and end dates is recorded for this
                partner.
              </p>
            )}
          </section>
          <section className="box">
            <h3>Open alerts ({partnerAlerts.length})</h3>
            {partnerAlerts.map((alert, index) => (
              <AlertRow
                key={alert.id}
                alert={alert}
                index={index}
                onSelect={onSelect}
              />
            ))}
            {!partnerAlerts.length && (
              <p>No record linked to this partner triggers a rule.</p>
            )}
          </section>
          <section className="box">
            <h3>Linked records</h3>
            <div className="detail-row">
              <span>Pipeline</span>
              <Link to="/pipeline">
                {d.opportunities.length} opportunit
                {d.opportunities.length === 1 ? "y" : "ies"}
              </Link>
            </div>
            <div className="detail-row">
              <span>Agreements</span>
              <Link to="/agreements">{d.agreements.length}</Link>
            </div>
            <div className="detail-row">
              <span>Projects</span>
              <Link to="/projects">
                {d.projects.length} · {done} of {d.milestones.length} milestones
                complete
              </Link>
            </div>
            <div className="detail-row">
              <span>Finance records</span>
              <Link to="/finance">{d.finance.length}</Link>
            </div>
            <div className="detail-row">
              <span>Reports not yet submitted</span>
              <Link to="/reports">
                {
                  d.reports.filter(
                    (r) => r.status !== "submitted" && r.status !== "accepted",
                  ).length
                }
              </Link>
            </div>
          </section>
          <section className="box">
            <h3>Recent activity</h3>
            {d.activities.map((a) => (
              <div className="detail-row" key={a.id}>
                <span>{a.summary}</span>
                <span className="mono">{a.at.slice(0, 10)}</span>
              </div>
            ))}
            {!d.activities.length && (
              <p>No reviews, tasks, or status changes recorded yet.</p>
            )}
          </section>
        </div>
      )}
      <Dialog
        open={editing}
        title="Edit partner"
        onClose={() => setEditing(false)}
      >
        {d && (
          <PartnerForm
            partner={d.partner}
            onCancel={() => setEditing(false)}
            onSaved={() => {
              setEditing(false);
              data.reload();
              onChanged();
            }}
          />
        )}
      </Dialog>
    </>
  );
}

/** Labels from the reference design mapped onto the API's lifecycle stages. */
const STAGE_LABELS: Record<string, string> = {
  identified: "Opportunity",
  agreement: "MOU",
  active: "Implementation",
  closed: "Closure",
};
const stageName = (stage: Opportunity["stage"]) =>
  STAGE_LABELS[stage] ?? stageLabel(stage);

const formatDate = (value: string | null): string =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(new Date(value))
    : "Not recorded";
const money = (value: number): string =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
function TableState({ message }: { message: string }) {
  return <p className="table-state">{message}</p>;
}
function PipelinePage({ onChanged }: { onChanged: () => void }) {
  const data = useResource(async () => {
    const [opportunities, partners] = await Promise.all([
      api.opportunities.list(),
      api.partners.list(),
    ]);
    return { opportunities, partners };
  }, []);
  const [dialog, setDialog] = useState<{ opportunity?: Opportunity } | null>(
    null,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const names = new Map((data.data?.partners ?? []).map((p) => [p.id, p.name]));
  const refresh = (text: string) => {
    setDialog(null);
    setMessage(text);
    data.reload();
    onChanged();
  };
  const move = async (item: Opportunity) => {
    const next = nextStage(item.stage);
    if (!next) return;
    setBusy(item.id);
    setMessage("");
    try {
      await api.opportunities.update(item.id, { stage: next });
      refresh(`Moved “${item.title}” to ${stageName(next)}.`);
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Could not move the opportunity.",
      );
    } finally {
      setBusy(null);
    }
  };
  return (
    <>
      <RegisterState
        resource={data}
        label="pipeline"
        message={message}
        action={
          <button
            className="btn small-btn"
            onClick={() => setDialog({})}
            disabled={!data.data}
          >
            Add opportunity
          </button>
        }
      />
      {data.data && (
        <div className="pipeline-grid">
          {STAGES.map(({ id: stage }) => {
            const column = data.data!.opportunities.filter(
              (item) => item.stage === stage,
            );
            return (
              <section className="pipeline-column" key={stage}>
                <h3>
                  {stageName(stage)}
                  <span className="pill">{column.length}</span>
                </h3>
                {column.length ? (
                  column.map((item) => (
                    <div className="pipeline-card" key={item.id}>
                      <b>{names.get(item.partner_id) ?? item.partner_id}</b>
                      <small>
                        {item.title} · {item.owner}
                      </small>
                      <p>{item.next_step || "No next step recorded"}</p>
                      <span className="mono">
                        {item.next_step_date
                          ? formatDate(item.next_step_date)
                          : "No date"}
                      </span>
                      {stage !== "closed" && (
                        <button
                          className="btn small-btn"
                          onClick={() => void move(item)}
                          disabled={busy === item.id}
                        >
                          {busy === item.id
                            ? "Moving…"
                            : `Move to ${stageName(nextStage(stage)!)}`}
                        </button>
                      )}
                      <button
                        className="text-button"
                        onClick={() => setDialog({ opportunity: item })}
                        aria-label={`Edit ${item.title}`}
                      >
                        Edit
                      </button>
                    </div>
                  ))
                ) : (
                  <TableState message="No opportunities" />
                )}
              </section>
            );
          })}
        </div>
      )}
      <Dialog
        open={dialog !== null}
        title={dialog?.opportunity ? "Edit opportunity" : "Add opportunity"}
        onClose={() => setDialog(null)}
      >
        {dialog && data.data && (
          <OpportunityForm
            opportunity={dialog.opportunity}
            partners={data.data.partners}
            onCancel={() => setDialog(null)}
            onSaved={(saved) => refresh(`Saved “${saved.title}”.`)}
            onDeleted={
              dialog.opportunity
                ? () => refresh(`Deleted “${dialog.opportunity!.title}”.`)
                : undefined
            }
          />
        )}
      </Dialog>
    </>
  );
}

/** Loading, error, and confirmation states plus a toolbar action for the API-backed registers. */
function RegisterState({
  resource,
  label,
  message,
  action,
}: {
  resource: {
    loading: boolean;
    error: Error | null;
    data: unknown;
    reload: () => void;
  };
  label: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <>
      {action && <div className="toolbar">{action}</div>}
      {resource.error && (
        <div className="api-state error" role="alert">
          <b>Could not load the {label}.</b>
          <span>{resource.error.message}</span>
          <button className="btn small-btn" onClick={resource.reload}>
            Retry
          </button>
        </div>
      )}
      {resource.loading && !resource.data && (
        <p className="api-state" role="status">
          Loading {label}…
        </p>
      )}
      {message && (
        <p className="api-state success" role="status">
          {message}
        </p>
      )}
    </>
  );
}

function AgreementsPage({ onChanged }: { onChanged: () => void }) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [dialog, setDialog] = useState<{ agreement?: Agreement } | null>(null);
  const [message, setMessage] = useState("");
  const data = useResource(async () => {
    // Expiry windows are evaluated by the backend on the IST business date; the browser only subtracts counts.
    const [agreements, partners, projects, opportunities, in30, in60, in90] =
      await Promise.all([
        api.agreements.list(),
        api.partners.list(),
        api.projects.list(),
        api.opportunities.list(),
        api.agreements.list(undefined, { expiring_within_days: "30" }),
        api.agreements.list(undefined, { expiring_within_days: "60" }),
        api.agreements.list(undefined, { expiring_within_days: "90" }),
      ]);
    return {
      agreements,
      partners,
      projects,
      opportunities,
      buckets: [
        ["0-30", in30.length],
        ["31-60", in60.length - in30.length],
        ["61-90", in90.length - in60.length],
      ] as [string, number][],
    };
  }, []);
  const names = new Map((data.data?.partners ?? []).map((p) => [p.id, p.name]));
  const refresh = (text: string) => {
    setDialog(null);
    setMessage(text);
    data.reload();
    onChanged();
  };
  const filtered = (data.data?.agreements ?? [])
    .filter(
      (a) =>
        `${names.get(a.partner_id) ?? ""} ${a.reference_number ?? ""} ${a.title}`
          .toLowerCase()
          .includes(query.toLowerCase()) &&
        (status === "all" || a.status === status),
    )
    .sort((a, b) =>
      (a.expiry_date ?? "9999").localeCompare(b.expiry_date ?? "9999"),
    );
  return (
    <>
      <RegisterState resource={data} label="agreements" message={message} />
      {data.data && (
        <>
          <div className="radar">
            {data.data.buckets.map(([label, count]) => (
              <div key={label}>
                <b>{count}</b>
                <span>Active, expiring in {label} days</span>
              </div>
            ))}
          </div>
          <section className="box">
            <div className="toolbar">
              <input
                className="search"
                placeholder="Search partner, title, or reference"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                aria-label="Search agreements"
              />
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
                aria-label="Filter by status"
              >
                <option value="all">All statuses</option>
                {AGREEMENT_STATUSES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
              <button className="btn small-btn" onClick={() => setDialog({})}>
                Add agreement
              </button>
            </div>
            <DataTable
              headers={[
                "Partner",
                "Agreement",
                "Status",
                "Start",
                "End",
                "Signed copy",
                "Owner",
                "Renewal",
                "Document",
                "",
              ]}
              rows={filtered.map((a) => [
                names.get(a.partner_id) ?? a.partner_id,
                <span key="t">
                  {a.title}
                  <small> · {a.reference_number ?? "No reference"}</small>
                </span>,
                <span className="pill" key="status">
                  {labelOf(AGREEMENT_STATUSES, a.status)}
                </span>,
                formatDate(a.start_date ?? null),
                formatDate(a.expiry_date ?? null),
                labelOf(SIGNED_COPY, a.signed_copy),
                a.owner,
                labelOf(RENEWAL, a.renewal_status),
                isWebLink(a.document_url) ? (
                  <a
                    key="doc"
                    href={a.document_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open
                  </a>
                ) : (
                  "None"
                ),
                <button
                  key="edit"
                  className="text-button"
                  onClick={() => setDialog({ agreement: a })}
                  aria-label={`Edit ${a.title}`}
                >
                  Edit
                </button>,
              ])}
              empty={
                data.data.agreements.length
                  ? "No agreements match the current filters."
                  : "No agreements recorded yet."
              }
            />
          </section>
        </>
      )}
      <Dialog
        open={dialog !== null}
        title={dialog?.agreement ? "Edit agreement" : "Add agreement"}
        onClose={() => setDialog(null)}
      >
        {dialog && data.data && (
          <AgreementForm
            agreement={dialog.agreement}
            partners={data.data.partners}
            projects={data.data.projects}
            opportunities={data.data.opportunities}
            onCancel={() => setDialog(null)}
            onSaved={(saved) => refresh(`Saved “${saved.title}”.`)}
            onDeleted={
              dialog.agreement
                ? () => refresh(`Deleted “${dialog.agreement!.title}”.`)
                : undefined
            }
          />
        )}
      </Dialog>
    </>
  );
}

function ProjectsPage({ onChanged }: { onChanged: () => void }) {
  const data = useResource(async () => {
    const [projects, milestones, partners] = await Promise.all([
      api.projects.list(),
      api.milestones.list(),
      api.partners.list(),
    ]);
    return { projects, milestones, partners };
  }, []);
  const [dialog, setDialog] = useState<
    | { kind: "project"; project?: Project }
    | {
        kind: "milestone";
        projectId: string;
        milestone?: Milestone;
        complete?: boolean;
      }
    | null
  >(null);
  const [message, setMessage] = useState("");
  const names = new Map((data.data?.partners ?? []).map((p) => [p.id, p.name]));
  const refresh = (text: string) => {
    setDialog(null);
    setMessage(text);
    data.reload();
    onChanged();
  };
  const milestoneStatus = (status: Milestone["status"]) =>
    MILESTONE_STATUSES.find((s) => s.id === status)?.label ?? status;
  const title = !dialog
    ? ""
    : dialog.kind === "project"
      ? dialog.project
        ? "Edit project"
        : "Add project"
      : dialog.complete
        ? "Mark milestone complete"
        : dialog.milestone
          ? "Edit milestone"
          : "Add milestone";
  return (
    <>
      <RegisterState
        resource={data}
        label="projects"
        message={message}
        action={
          <button
            className="btn small-btn"
            onClick={() => setDialog({ kind: "project" })}
            disabled={!data.data}
          >
            Add project
          </button>
        }
      />
      {data.data &&
        (data.data.projects.length ? (
          <div className="project-grid">
            {data.data.projects.map((project) => {
              const milestones = data
                .data!.milestones.filter((m) => m.project_id === project.id)
                .sort((a, b) =>
                  (a.due_date ?? "9999").localeCompare(b.due_date ?? "9999"),
                );
              const complete = milestones.filter(
                (m) => m.status === "completed",
              ).length;
              return (
                <section className="box project-card" key={project.id}>
                  <div className="card-heading">
                    <div>
                      <h3>{project.name}</h3>
                      <p>
                        {project.partner_id
                          ? (names.get(project.partner_id) ??
                            project.partner_id)
                          : "No partner"}
                      </p>
                    </div>
                    <span className="pill">
                      {project.status.replace("_", " ")}
                    </span>
                  </div>
                  <div className="project-meta">
                    <span>Owner: {project.owner}</span>
                    <span>
                      {formatDate(project.start_date ?? null)} –{" "}
                      {formatDate(project.end_date ?? null)}
                    </span>
                  </div>
                  <div
                    className="progress"
                    role="img"
                    aria-label={`${complete} of ${milestones.length} milestones complete`}
                  >
                    <i
                      style={{
                        width: `${milestones.length ? (complete / milestones.length) * 100 : 0}%`,
                      }}
                    />
                  </div>
                  <small>
                    {milestones.length
                      ? `${complete} of ${milestones.length} milestones complete`
                      : "No milestones recorded"}
                  </small>
                  <div className="milestones">
                    {milestones.map((m) => (
                      <div className="milestone" key={m.id}>
                        <span>{m.title}</span>
                        <span
                          className={m.status === "missed" ? "text-bordo" : ""}
                        >
                          {milestoneStatus(m.status)} ·{" "}
                          {formatDate(m.due_date ?? null)}
                          {m.completed_date
                            ? ` · done ${formatDate(m.completed_date)}`
                            : ""}
                        </span>
                        <span>
                          {m.status !== "completed" &&
                            m.status !== "cancelled" && (
                              <button
                                className="text-button"
                                onClick={() =>
                                  setDialog({
                                    kind: "milestone",
                                    projectId: project.id,
                                    milestone: m,
                                    complete: true,
                                  })
                                }
                                aria-label={`Mark ${m.title} complete`}
                              >
                                Complete
                              </button>
                            )}
                          <button
                            className="text-button"
                            onClick={() =>
                              setDialog({
                                kind: "milestone",
                                projectId: project.id,
                                milestone: m,
                              })
                            }
                            aria-label={`Edit ${m.title}`}
                          >
                            Edit
                          </button>
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="button-row">
                    <button
                      className="btn small-btn"
                      onClick={() =>
                        setDialog({ kind: "milestone", projectId: project.id })
                      }
                    >
                      Add milestone
                    </button>
                    <button
                      className="text-button"
                      onClick={() => setDialog({ kind: "project", project })}
                      aria-label={`Edit ${project.name}`}
                    >
                      Edit project
                    </button>
                  </div>
                </section>
              );
            })}
          </div>
        ) : (
          <TableState message="No projects recorded yet." />
        ))}
      <Dialog
        open={dialog !== null}
        title={title}
        onClose={() => setDialog(null)}
      >
        {dialog?.kind === "project" && data.data && (
          <ProjectForm
            project={dialog.project}
            partners={data.data.partners}
            onCancel={() => setDialog(null)}
            onSaved={(saved) => refresh(`Saved “${saved.name}”.`)}
            onDeleted={
              dialog.project
                ? () => refresh(`Deleted “${dialog.project!.name}”.`)
                : undefined
            }
          />
        )}
        {dialog?.kind === "milestone" && (
          <MilestoneForm
            projectId={dialog.projectId}
            milestone={dialog.milestone}
            markComplete={dialog.complete}
            onCancel={() => setDialog(null)}
            onSaved={(saved) =>
              refresh(
                dialog.complete
                  ? `Marked “${saved.title}” complete.`
                  : `Saved “${saved.title}”.`,
              )
            }
            onDeleted={
              dialog.milestone && !dialog.complete
                ? () => refresh(`Deleted “${dialog.milestone!.title}”.`)
                : undefined
            }
          />
        )}
      </Dialog>
    </>
  );
}

function FinanceSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="box">
      <h3>{title}</h3>
      {children}
    </section>
  );
}
// Allowed statuses per finance record type (mirrors FINANCE_STATUSES in backend/app/models.py).
const FINANCE_STATUS_OPTIONS: Record<FinanceRecord["record_type"], string[]> = {
  budget: ["planned", "approved", "revised", "closed"],
  fund_received: ["expected", "received", "cancelled"],
  invoice: ["raised", "draft", "sent", "paid", "cancelled"],
  utilization_certificate: ["pending", "submitted", "accepted", "rejected"],
};
const FINANCE_SECTIONS: { type: FinanceRecord["record_type"]; title: string }[] = [
  { type: "budget", title: "Budgets" },
  { type: "fund_received", title: "Funds received" },
  { type: "invoice", title: "Invoices" },
  { type: "utilization_certificate", title: "Utilization certificates" },
];

/** Amount in the record's own currency; amounts are never added across records, types, or currencies. */
const recordAmount = (record: FinanceRecord): string =>
  record.amount == null
    ? "Amount not recorded"
    : new Intl.NumberFormat("en-IN", { style: "currency", currency: record.currency || "INR", maximumFractionDigits: 0 }).format(record.amount);

function FinancePage() {
  const data = useResource(async () => {
    const [records, partners, alerts] = await Promise.all([api.finance.list(), api.partners.list(), api.alerts.list()]);
    return { records, partners, alerts };
  }, []);
  const [message, setMessage] = useState("");
  const names = new Map((data.data?.partners ?? []).map((p) => [p.id, p.name]));
  // Ageing and overdue wording come from the rules engine (alerts), not from date maths in the browser.
  const alertFor = new Map((data.data?.alerts.alerts ?? []).filter((a) => a.record_type === "finance").map((a) => [a.record_id, a]));
  const setStatus = async (record: FinanceRecord, status: string) => {
    setMessage("");
    try {
      await api.finance.update(record.id, { status });
      setMessage(`“${record.title}” is now ${status.replace("_", " ")}.`);
      data.reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not update the record.");
    }
  };
  return (
    <>
      <RegisterState resource={data} label="finance records" message={message} />
      {data.data && (
        <div className="finance-sections">
          {FINANCE_SECTIONS.map(({ type, title }) => {
            const records = data.data!.records.filter((r) => r.record_type === type);
            return (
              <FinanceSection title={title} key={type}>
                {records.length ? (
                  records.map((record) => {
                    const alert = alertFor.get(record.id);
                    const dates = [
                      record.issue_date && `issued ${formatDate(record.issue_date)}`,
                      record.due_date ? `due ${formatDate(record.due_date)}` : type === "invoice" || type === "utilization_certificate" ? "due date not recorded" : "",
                      record.received_date && `received ${formatDate(record.received_date)}`,
                    ].filter(Boolean);
                    return (
                      <div className="finance-row" key={record.id}>
                        <span>
                          <b>{`${names.get(record.partner_id) ?? record.partner_id} · ${record.title}`}</b>
                          <small>
                            {dates.join(" · ")}
                            {alert ? ` · ⚠ ${alert.rule_title}` : ""}
                            {record.source_label === "demo" ? " · fictional demo record" : ""}
                          </small>
                          <select
                            aria-label={`Status of ${record.title}`}
                            value={record.status}
                            onChange={(event) => void setStatus(record, event.target.value)}
                          >
                            {(FINANCE_STATUS_OPTIONS[record.record_type] ?? [record.status]).map((s) => (
                              <option key={s} value={s}>
                                {s.replace("_", " ")}
                              </option>
                            ))}
                          </select>
                        </span>
                        <strong className="mono">{recordAmount(record)}</strong>
                      </div>
                    );
                  })
                ) : (
                  <p>No {title.toLowerCase()} recorded.</p>
                )}
              </FinanceSection>
            );
          })}
        </div>
      )}
    </>
  );
}

type ObligationRow = {
  id: string; kind: "report" | "uc"; type: string; title: string; partnerId: string; dueDate?: string | null;
  status: string; owner: string; overdue: boolean; done: boolean; demo: boolean;
};

function ReportsPage() {
  const data = useResource(async () => {
    const [reports, finance, partners, alerts] = await Promise.all([
      api.reports.list(), api.finance.list(undefined, { record_type: "utilization_certificate" }), api.partners.list(), api.alerts.list(),
    ]);
    return { reports, finance, partners, alerts };
  }, []);
  const [tab, setTab] = useState("All");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [submittedOn, setSubmittedOn] = useState("");
  const names = new Map((data.data?.partners ?? []).map((p) => [p.id, p.name]));
  const overdueIds = new Set((data.data?.alerts.alerts ?? []).filter((a) => a.rule_id === "REPORT_OVERDUE" || a.rule_id === "UC_OVERDUE").map((a) => a.record_id));
  const rows: ObligationRow[] = [
    ...(data.data?.reports ?? []).map((r) => ({
      id: r.id, kind: "report" as const, type: `${r.report_type} report`, title: r.title, partnerId: r.partner_id, dueDate: r.due_date,
      status: r.status, owner: r.owner, overdue: overdueIds.has(r.id), done: r.status === "submitted" || r.status === "accepted", demo: r.source_label === "demo",
    })),
    ...(data.data?.finance ?? []).map((f) => ({
      id: f.id, kind: "uc" as const, type: "Utilization certificate", title: f.title, partnerId: f.partner_id, dueDate: f.due_date,
      status: f.status, owner: "—", overdue: overdueIds.has(f.id), done: ["submitted", "accepted"].includes(f.status), demo: f.source_label === "demo",
    })),
  ];
  const filtered = rows.filter((r) =>
    tab === "All" ? true : tab === "Overdue" ? r.overdue : tab === "Submitted" ? r.done : !r.done && !r.overdue,
  );
  const markSubmitted = async (row: ObligationRow) => {
    setMessage("");
    try {
      if (row.kind === "report") await api.reports.update(row.id, { status: "submitted", submitted_date: submittedOn });
      else await api.finance.update(row.id, { status: "submitted" });
      setMessage(`Marked “${row.title}” submitted.`);
      setSubmitting(null);
      setSubmittedOn("");
      data.reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not update the record.");
    }
  };
  return (
    <section className="box">
      <RegisterState resource={data} label="reports and utilization certificates" message={message} />
      <div className="tabs report-tabs">
        {["All", "Pending", "Overdue", "Submitted"].map((item) => (
          <button className={tab === item ? "active" : ""} key={item} onClick={() => setTab(item)}>
            {item} ({item === "All" ? rows.length : rows.filter((r) => (item === "Overdue" ? r.overdue : item === "Submitted" ? r.done : !r.done && !r.overdue)).length})
          </button>
        ))}
      </div>
      {data.data && (
        <DataTable
          headers={["Type", "Title", "Partner", "Due", "Status", "Owner", ""]}
          rows={filtered.map((row) => [
            row.type,
            row.title,
            names.get(row.partnerId) ?? row.partnerId,
            row.dueDate ? formatDate(row.dueDate) : "Due date not recorded",
            <span className={`pill ${row.overdue ? "high" : ""}`} key="status">
              {row.overdue ? "Overdue" : row.status.replace("_", " ")}
            </span>,
            row.owner,
            row.done ? (
              ""
            ) : submitting === row.id && row.kind === "report" ? (
              <span className="button-row" key="submit">
                <input type="date" aria-label="Submitted on" value={submittedOn} onChange={(e) => setSubmittedOn(e.target.value)} />
                <button className="btn small-btn" disabled={!submittedOn} onClick={() => void markSubmitted(row)}>
                  Save
                </button>
              </span>
            ) : (
              <button
                className="btn outline small-btn"
                key="submit"
                onClick={() => (row.kind === "report" ? setSubmitting(row.id) : void markSubmitted(row))}
              >
                Mark submitted
              </button>
            ),
          ])}
          empty="No reports or utilization certificates match this tab."
        />
      )}
    </section>
  );
}

function documentStatus(document: SourceDocument): string {
  if (document.status === "blocked")
    return document.kind === "addendum" && !document.agreement_id
      ? "Unlinked addendum"
      : "Needs OCR";
  return document.status === "needs_review"
    ? "Needs Review"
    : document.status[0].toUpperCase() + document.status.slice(1);
}

function DocumentsPage({ partners }: { partners: Partner[] }) {
  const data = useResource(() => api.documents.list(), []);
  const [kind, setKind] = useState<"mou" | "addendum">("mou");
  const [partnerId, setPartnerId] = useState("");
  const [agreementId, setAgreementId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploaded, setUploaded] = useState<SourceDocument | null>(null);
  const upload = async (file: File) => {
    setBusy(true);
    setError("");
    setUploaded(null);
    try {
      const saved = await api.documents.upload(
        file,
        kind,
        partnerId || undefined,
        agreementId || undefined,
      );
      setUploaded(saved);
      data.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="toolbar">
        <label>
          Type{" "}
          <select
            value={kind}
            onChange={(event) =>
              setKind(event.target.value as "mou" | "addendum")
            }
          >
            <option value="mou">MOU</option>
            <option value="addendum">Addendum</option>
          </select>
        </label>
        <label>
          Partner{" "}
          <select
            value={partnerId}
            onChange={(event) => setPartnerId(event.target.value)}
          >
            <option value="">Select partner</option>
            {partners.map((partner) => (
              <option value={partner.id} key={partner.id}>
                {partner.name}
              </option>
            ))}
          </select>
        </label>
        <label className="dropzone compact">
          {busy ? "Uploading…" : "Upload PDF"}
          <input
            type="file"
            accept="application/pdf,.pdf"
            disabled={busy}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
            }}
          />
        </label>
      </div>
      {error && (
        <p className="api-state error" role="alert">
          {error}
        </p>
      )}
      {uploaded && (
        <div className="api-state success" role="status">
          <span>
            Uploaded “{uploaded.filename}” ({uploaded.page_count ?? "?"} pages,{" "}
            {documentStatus(uploaded)}). Nothing has been extracted yet.
          </span>
          <Link className="btn small-btn" to={`/documents/${uploaded.id}`}>
            Open to extract and review
          </Link>
        </div>
      )}
      {data.error && (
        <p className="api-state error" role="alert">
          {data.error.message}
          <button className="btn small-btn" onClick={data.reload}>
            Retry
          </button>
        </p>
      )}
      {data.loading && !data.data && (
        <p className="api-state" role="status">
          Loading documents…
        </p>
      )}
      <section className="box">
        <h3>
          Source documents{" "}
          <small>Synthetic demo data is not used for uploaded documents.</small>
        </h3>
        <DataTable
          headers={[
            "Filename",
            "Type",
            "Partner",
            "Agreement",
            "Uploaded",
            "Status",
          ]}
          rows={(data.data ?? []).map((document) => [
            <Link to={`/documents/${document.id}`} key={document.id}>
              {document.filename}
            </Link>,
            document.kind.toUpperCase(),
            partners.find((partner) => partner.id === document.partner_id)
              ?.name ?? "Not linked",
            document.agreement_id ?? "Not linked",
            formatDate(document.uploaded_at),
            <span
              className={`pill ${document.status === "failed" || document.status === "blocked" ? "high" : ""}`}
              key="status"
            >
              {documentStatus(document)}
            </span>,
          ])}
          empty="No documents uploaded yet."
        />
      </section>
    </>
  );
}

const DECIDABLE: { key: Exclude<ProposalCollection, "extracted_fields">; label: string }[] = [
  { key: "tables", label: "Tables" },
  { key: "obligations", label: "Obligations and deadlines" },
  { key: "financial_terms", label: "Financial terms" },
  { key: "clauses", label: "Clauses" },
  { key: "programme_scope", label: "Programme scope" },
];

const PENDING_STATES = ["proposed", "needs_review"];

function deadlineText(o: ObligationProposal): string {
  if (o.due_date) return `due ${formatDate(o.due_date)}`;
  const d = o.deadline;
  if (!d || d.deadline_type === "unspecified") return "no deadline stated";
  if (d.text) return `“${d.text}”`;
  return d.recurrence ? `${d.recurrence} (recurring)` : d.deadline_type;
}

function proposalSummary(collection: string, item: Record<string, unknown>): string {
  const r = item as unknown as ClauseProposal & FinancialTermProposal & ObligationProposal & ScopeProposal & TableProposal;
  switch (collection) {
    case "clauses":
      return `${r.clause_type.replaceAll("_", " ")}: ${r.summary}`;
    case "financial_terms":
      return `${r.term_type.replaceAll("_", " ")}: ${r.description} — ${r.amount != null && r.currency ? `${r.currency} ${r.amount.toLocaleString("en-IN")} (${r.basis})` : "amount not stated"}`;
    case "obligations":
      return `${r.obligation_type.replaceAll("_", " ")}: ${r.title} — ${deadlineText(r as ObligationProposal)}`;
    case "programme_scope":
      return `${r.dimension.replaceAll("_", " ")}: ${r.value}${r.location ? ` · ${r.location}` : ""}${r.target_value != null ? ` · ${r.target_value} ${r.target_unit ?? ""}` : ""}`;
    case "tables":
      return `${r.title} (${r.kind}${r.section ? ` · ${r.section}` : ""}) — ${r.rows.length} rows, pages ${r.pages.join(", ")}`;
    default:
      return "";
  }
}

function EvidenceLine({ evidence, onShow }: { evidence?: DocumentEvidence | null; onShow: (page: number) => void }) {
  if (!evidence) return <span className="mono">Evidence not recorded</span>;
  return (
    <span className="mono">
      <button className="text-button" type="button" onClick={() => onShow(evidence.page)}>
        Page {evidence.page}
        {evidence.printed_page ? ` (printed ${evidence.printed_page})` : ""}
        {evidence.section ? ` · ${evidence.section}` : ""}
      </button>
      : “{evidence.quote}” ·{" "}
      {evidence.verified
        ? evidence.basis === "ai_transcript"
          ? "found in the AI reading of a scanned page — compare with the image"
          : "found in the PDF text"
        : "not found on that page"}
    </span>
  );
}

function PageViewer({ documentId, pageCount, page, onPage }: { documentId: string; pageCount: number; page: number; onPage: (page: number) => void }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    setError("");
    setUrl(null);
    api.documents
      .pageImage(documentId, page)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((err) => active && setError(err instanceof Error ? err.message : "Could not load the page."));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, page]);
  return (
    <div className="page-viewer">
      <div className="toolbar">
        <button className="btn small-btn" type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          ‹ Previous
        </button>
        <label>
          Page{" "}
          <select value={page} onChange={(event) => onPage(Number(event.target.value))}>
            {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>{" "}
          of {pageCount}
        </label>
        <button className="btn small-btn" type="button" disabled={page >= pageCount} onClick={() => onPage(page + 1)}>
          Next ›
        </button>
      </div>
      {error && (
        <p className="api-state error" role="alert">
          {error}
        </p>
      )}
      {!url && !error && (
        <p className="api-state" role="status">
          Loading page {page}…
        </p>
      )}
      {url && <img src={url} alt={`Page ${page} of the source document`} />}
    </div>
  );
}

function DocumentReviewPage({ partners, onApproved }: { partners: Partner[]; onApproved: () => void }) {
  const location = useLocation();
  const documentId = location.pathname.split("/")[2] ?? "";
  const data = useResource<DocumentReview>(() => api.documents.review(documentId), [documentId]);
  const [partnerId, setPartnerId] = useState("");
  const [createPartner, setCreatePartner] = useState(false);
  const check = useResource(
    () => api.documents.approvalCheck(documentId, { partnerId: partnerId || undefined, createPartner }),
    [documentId, partnerId, createPartner, data.data],
  );
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const status = data.data?.document.status;
  // While extraction runs in the background, refresh every few seconds to show progress.
  useEffect(() => {
    if (status !== "extracting") return;
    const timer = window.setTimeout(data.reload, 3000);
    return () => window.clearTimeout(timer);
  }, [status, data.data, data.reload]);
  if (data.loading && !data.data)
    return (
      <p className="api-state" role="status">
        Loading review workspace…
      </p>
    );
  if (data.error)
    return (
      <p className="api-state error" role="alert">
        {data.error.message}
        <button className="btn small-btn" onClick={data.reload}>
          Retry
        </button>
      </p>
    );
  const review = data.data;
  if (!review) return <p className="api-state">No review data available.</p>;
  const doc = review.document;
  const locked = doc.status !== "needs_review";
  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setMessage("");
    try {
      await action();
      setMessage(success);
      data.reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "The request failed.");
    } finally {
      setBusy(false);
    }
  };
  const decide = (collection: ProposalCollection, item: { id: string }, decision: "approve" | "reject" | "defer", value?: string | number | boolean | null) =>
    void run(
      () => api.documents.decide(documentId, collection, item.id, { decision, value, note: notes[item.id] || undefined }),
      `Saved: ${decision === "approve" ? "approved" : decision === "reject" ? "rejected" : "deferred"}.`,
    );
  const noteInput = (id: string, label: string) => (
    <input
      aria-label={label}
      placeholder="Note (needed to defer, or to approve an unverified quote)"
      value={notes[id] ?? ""}
      onChange={(event) => setNotes({ ...notes, [id]: event.target.value })}
      disabled={busy || locked}
    />
  );
  const decisionButtons = (collection: ProposalCollection, item: { id: string; review_state: string }, value?: string | number | boolean | null, canApprove = true) => (
    <span className="button-row">
      <button className="btn small-btn" disabled={busy || locked || !canApprove} onClick={() => decide(collection, item, "approve", value)}>
        {item.review_state === "approved" ? "Approved" : "Approve"}
      </button>
      <button className="btn outline small-btn" disabled={busy || locked} onClick={() => decide(collection, item, "reject")}>
        Reject
      </button>
      <button className="btn outline small-btn" disabled={busy || locked} onClick={() => decide(collection, item, "defer")}>
        Defer
      </button>
    </span>
  );
  const extraction = doc.extraction;
  const canExtract = ["uploaded", "failed", "blocked", "needs_review"].includes(doc.status);
  const pending = [...review.fields, ...DECIDABLE.flatMap(({ key }) => review[key] as { review_state: string }[])].filter((i) =>
    PENDING_STATES.includes(i.review_state),
  ).length;
  return (
    <>
      <section className="box">
        <h3>
          {doc.filename}{" "}
          <span className={`pill ${doc.status === "failed" || doc.status === "blocked" ? "high" : ""}`}>{documentStatus(doc)}</span>
        </h3>
        <p>
          {doc.kind.toUpperCase()} · {doc.page_count ?? "?"} pages · uploaded {formatDate(doc.uploaded_at)} by {doc.uploaded_by}
          {doc.partner_id ? ` · ${partners.find((p) => p.id === doc.partner_id)?.name ?? doc.partner_id}` : " · no partner linked"}
        </p>
        {doc.warnings.map((warning) => (
          <p className="api-state" key={warning}>
            {warning}
          </p>
        ))}
        {doc.error && (
          <p className="api-state error" role="alert">
            {doc.error}
          </p>
        )}
        {doc.status === "extracting" && extraction && (
          <p className="api-state" role="status">
            {extraction.pages_read < extraction.pages_to_read
              ? `Reading scanned pages with Gemini: ${extraction.pages_read} of ${extraction.pages_to_read}…`
              : `Extracting values: part ${extraction.chunks_done} of ${extraction.chunks_total || "?"}…`}
          </p>
        )}
        {canExtract && (
          <div className="button-row">
            <button
              className="btn small-btn"
              disabled={busy}
              onClick={() => void run(() => api.documents.extract(documentId), "")}
            >
              {doc.status === "needs_review" ? "Re-run extraction" : "Read & extract with Gemini"}
            </button>
          </div>
        )}
        {doc.status === "approved" && <p className="api-state success">Approved by {doc.approved_by}. Values are now operational records.</p>}
      </section>
      <div className="review-workspace">
        <section className="box">
          <h3>Review fields</h3>
          {review.fields.length ? (
            review.fields.map((field) => (
              <div className="review-field" key={field.id}>
                <div>
                  <b>{field.field.replaceAll("_", " ")}</b>
                  <small>
                    Proposed: {String(field.approved_value ?? field.proposed_value ?? "—")} · as written: {field.verbatim || "No verbatim source text recorded."}
                  </small>
                  <EvidenceLine evidence={field.evidence} onShow={setPage} />
                  {field.warnings.map((w) => (
                    <small key={w}>⚠ {w}</small>
                  ))}
                  {!locked && noteInput(field.id, `Note for ${field.field}`)}
                </div>
                <span className={`pill ${field.review_state === "approved" ? "" : "high"}`}>{field.review_state.replace("_", " ")}</span>
                {decisionButtons("extracted_fields", field, field.proposed_value ?? null, field.proposed_value != null)}
              </div>
            ))
          ) : (
            <p>No extracted fields are available. Extraction must complete before human review.</p>
          )}
          {DECIDABLE.map(({ key, label }) => {
            const items = review[key] as unknown as (Record<string, unknown> & { id: string; review_state: string; warnings: string[]; evidence?: DocumentEvidence | null })[];
            if (!items.length) return null;
            return (
              <div key={key}>
                <h3>{label}</h3>
                {items.map((item) => (
                  <div className="review-field" key={item.id}>
                    <div>
                      <b>{proposalSummary(key, item)}</b>
                      {key === "tables" && <ReviewTable table={item as unknown as TableProposal} />}
                      <EvidenceLine evidence={item.evidence} onShow={setPage} />
                      {item.warnings.map((w) => (
                        <small key={w}>⚠ {w}</small>
                      ))}
                      {!locked && noteInput(item.id, `Note for ${label}`)}
                    </div>
                    <span className={`pill ${item.review_state === "approved" ? "" : "high"}`}>{item.review_state.replace("_", " ")}</span>
                    {decisionButtons(key, item)}
                  </div>
                ))}
              </div>
            );
          })}
          {review.issues.length > 0 && <h3>Issues to resolve</h3>}
          {review.issues.map((issue) => (
            <div className="review-field" key={issue.id}>
              <div>
                <b>
                  {issue.code.replaceAll("_", " ").toLowerCase()} ({issue.severity})
                </b>
                <small>{issue.message}</small>
                {issue.resolution && <small>Resolution: {issue.resolution}</small>}
                {!locked && issue.status === "open" && noteInput(issue.id, `Resolution for ${issue.code}`)}
              </div>
              <span className={`pill ${issue.status === "open" ? "high" : ""}`}>{issue.status}</span>
              {!locked && issue.status === "open" && (
                <span className="button-row">
                  <button
                    className="btn small-btn"
                    disabled={busy || !notes[issue.id]}
                    onClick={() => void run(() => api.documents.resolveIssue(documentId, issue.id, { status: "resolved", resolution: notes[issue.id] }), "Issue resolved.")}
                  >
                    Resolve
                  </button>
                  <button
                    className="btn outline small-btn"
                    disabled={busy || !notes[issue.id]}
                    onClick={() => void run(() => api.documents.resolveIssue(documentId, issue.id, { status: "deferred", resolution: notes[issue.id] }), "Issue deferred.")}
                  >
                    Defer
                  </button>
                </span>
              )}
            </div>
          ))}
        </section>
        <aside className="box evidence-panel">
          <h3>Source page</h3>
          {(doc.page_count ?? 0) > 0 ? (
            <PageViewer documentId={documentId} pageCount={doc.page_count ?? 0} page={Math.min(page, doc.page_count ?? 1)} onPage={setPage} />
          ) : (
            <p>The file could not be read, so there are no pages to show.</p>
          )}
        </aside>
      </div>
      <div className="review-footer">
        <span>
          {pending} awaiting a decision · {review.issues.filter((i) => i.status === "open").length} open issues
        </span>
        {!doc.partner_id && !locked && (
          <span className="button-row">
            <select aria-label="Partner for this agreement" value={partnerId} onChange={(event) => setPartnerId(event.target.value)}>
              <option value="">Choose partner</option>
              {partners.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <label>
              <input type="checkbox" checked={createPartner} onChange={(event) => setCreatePartner(event.target.checked)} /> or create it from the
              approved partner name
            </label>
          </span>
        )}
        <button
          className="btn"
          disabled={busy || locked || !check.data?.ready}
          onClick={() =>
            void run(async () => {
              await api.documents.approve(documentId, { partner_id: partnerId || undefined, create_partner: createPartner || undefined });
              onApproved();
            }, "Approved: the agreement and its obligations are now operational records, and alerts were recalculated.")
          }
        >
          Approve records
        </button>
      </div>
      {!locked && check.data && !check.data.ready && (
        <ul className="api-state" aria-label="What still blocks approval">
          {check.data.blockers.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      )}
      {message && (
        <p className="api-state" role="status">
          {message}
        </p>
      )}
    </>
  );
}

function ReviewTable({ table }: { table: TableProposal }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Page</th>
            {table.headers.map((h, i) => (
              <th key={`${h}-${i}`}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.row_index} className={row.verified ? "" : "row-unverified"} title={row.verified ? undefined : "Cells not found on that page"}>
              <td>
                {row.page}
                {row.verified ? "" : " ⚠"}
              </td>
              {table.headers.map((_, i) => (
                <td key={i}>{row.cells[i] ?? ""}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {[...table.unit_notes, ...table.notes].map((n) => (
        <small key={n}>{n}</small>
      ))}
    </div>
  );
}

function ImportPage() {
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<"import" | "export">("import");
  const [exportMessage, setExportMessage] = useState("");
  const parse = async (file: File) => {
    setBusy(true);
    setPreview(null);
    setMessage("");
    try {
      const result = await api.importPreview(file, "projects");
      setPreview(result);
      setMessage(
        `${result.total_rows_detected} rows previewed from ${file.name}. No records were written.`,
      );
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Could not read this file.",
      );
    } finally {
      setBusy(false);
    }
  };
  const exportWorkbook = async () => {
    setExportMessage("Preparing approved workbook…");
    try {
      const blob = await api.documents.exportWorkbook();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "obligot-approved-workbook.xlsx";
      anchor.click();
      URL.revokeObjectURL(url);
      setExportMessage("Workbook downloaded from the backend.");
    } catch (err) {
      setExportMessage(
        err instanceof Error ? err.message : "Workbook export failed.",
      );
    }
  };
  return (
    <div className="import-flow">
      <div className="tabs">
        <button
          className={tab === "import" ? "active" : ""}
          onClick={() => setTab("import")}
        >
          Import preview
        </button>
        <button
          className={tab === "export" ? "active" : ""}
          onClick={() => setTab("export")}
        >
          Export workbook
        </button>
      </div>
      {tab === "export" ? (
        <section className="box">
          <h3>Approved-record export</h3>
          <p>
            Only backend-approved document-derived records are included.
            Proposed AI values are never exported.
          </p>
          <p className="mono">
            Sheets: Partners · Agreements · Programmes · Financial Terms ·
            Obligations & Reporting · Clauses · Amendments & Change History ·
            Validation Issues
          </p>
          <button className="btn" onClick={() => void exportWorkbook()}>
            Download .xlsx
          </button>
          {exportMessage && (
            <p className="import-message" role="status">
              {exportMessage}
            </p>
          )}
        </section>
      ) : (
        <>
          <label className="dropzone">
            {busy
              ? "Reading file on the server…"
              : "Drop a CSV or XLSX file here"}
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void parse(file);
              }}
            />
          </label>
          {message && !preview && (
            <p className="import-message" role="alert">
              {message}
            </p>
          )}
          {preview && (
            <>
              <section className="box">
                <h3>Preview · detected columns</h3>
                <div className="mapping">
                  {preview.headers.length ? (
                    preview.headers.map((header) => (
                      <b key={header}>{header || "(blank header)"}</b>
                    ))
                  ) : (
                    <span>No header row found.</span>
                  )}
                </div>
              </section>
              <section className="box validation">
                <h3>Validation summary</h3>
                <div>
                  <span className="pill">Valid · {preview.valid_count}</span>
                  <span className="pill high">
                    Invalid · {preview.invalid_count}
                  </span>
                </div>
                {preview.issues.slice(0, 5).map((issue) => (
                  <p key={issue.row}>
                    Row {issue.row}: {issue.issues.join("; ")}
                  </p>
                ))}
                <p>{preview.warning}</p>
              </section>
              <button
                className="btn"
                disabled
                title="Saving imported rows arrives in Step 10"
              >
                Confirm import (available in Step 10)
              </button>
              <p className="import-message">{message}</p>
            </>
          )}
        </>
      )}
    </div>
  );
}

function DataTable({
  headers,
  rows,
  empty,
}: {
  headers: string[];
  rows: Array<Array<ReactNode>>;
  empty: string;
}) {
  return rows.length ? (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <TableState message={empty} />
  );
}

function Drawer({
  alert,
  asOf,
  onClose,
  onChanged,
}: {
  alert: Alert;
  asOf: string;
  onClose: () => void;
  onChanged: (message: string) => void;
}) {
  const [ai, setAi] = useState<AnalyzeResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [mode, setMode] = useState<"none" | "task" | "defer" | "dismiss">(
    "none",
  );
  const [owner, setOwner] = useState(
    alert.owner === "Unassigned" ? "" : alert.owner,
  );
  const [due, setDue] = useState("");
  const [deferUntil, setDeferUntil] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const run = async () => {
    setRunning(true);
    setAi(null);
    const context = [
      `Alert: ${alert.ruleTitle}. ${alert.ruleDescription}`,
      ...alert.facts.map((fact) => `${fact.label}: ${fact.value}`),
      ...alert.computed.map(
        (fact) => `${fact.label} (computed): ${fact.value}`,
      ),
      `Rule-based next step: ${alert.recommendation}`,
    ].join("\n");
    try {
      setAi(
        await api.analyze({
          partner_id: alert.partnerId ?? undefined,
          context,
        }),
      );
    } catch (err) {
      setAi({
        summary: err instanceof Error ? err.message : "The AI request failed.",
        observations: [],
        recommendations: [],
        ai_used: false,
        ai_error: "request_failed",
      });
    } finally {
      setRunning(false);
    }
  };
  const act = async (action: () => Promise<unknown>, message: string) => {
    setBusy(true);
    setError("");
    try {
      await action();
      onChanged(message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The request failed.");
    } finally {
      setBusy(false);
    }
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (mode === "task") {
      if (owner.trim().length < 2) {
        setError("Assign a responsible owner (at least 2 characters).");
        return;
      }
      void act(
        () =>
          api.alerts.createTask(alert.id, {
            owner: owner.trim(),
            due_date: due || null,
          }),
        `Follow-up task created for ${owner.trim()}.`,
      );
    }
    if (mode === "defer") {
      if (!deferUntil) {
        setError("Choose the date to bring this alert back.");
        return;
      }
      void act(
        () =>
          api.alerts.review(alert.id, {
            decision: "deferred",
            deferred_until: deferUntil,
          }),
        `Deferred until ${formatDate(deferUntil)}.`,
      );
    }
    if (mode === "dismiss") {
      if (reason.trim().length < 5) {
        setError(
          "Give a reason of at least 5 characters; it is recorded in the activity log.",
        );
        return;
      }
      void act(
        () =>
          api.alerts.review(alert.id, {
            decision: "dismissed",
            reason: reason.trim(),
          }),
        "Alert dismissed. It returns if the record changes.",
      );
    }
  };
  const minDefer = (() => {
    const d = new Date(`${asOf}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + 1);
    return d.toISOString().slice(0, 10);
  })();
  return (
    <div
      className="drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
    >
      <button
        className="close"
        onClick={onClose}
        aria-label="Close alert details"
      >
        ×
      </button>
      <span
        className={`pill ${alert.priority === "High" ? "high" : "outline-pill"}`}
      >
        {alert.priority} · score {alert.score}
        {alert.review ? ` · ${alert.review.decision.replace("_", " ")}` : ""}
      </span>
      <h2 id="drawer-title">
        {alert.partner}: {alert.title}
      </h2>
      <DrawerSection title="Verified record facts">
        {alert.facts.map((fact) => (
          <div className="evidence" key={fact.label}>
            <span className="mono">{fact.label}</span>
            <b className="mono">{String(fact.value)}</b>
          </div>
        ))}
        <div className="evidence">
          <span>Owner</span>
          <b>{alert.owner}</b>
        </div>
        {alert.demo && <small>From a fictional demo record.</small>}
      </DrawerSection>
      {alert.computed.length > 0 && (
        <DrawerSection
          title={`Computed by the rule · as of ${formatDate(asOf)}`}
        >
          {alert.computed.map((fact) => (
            <div className="evidence" key={fact.label}>
              <span className="mono">{fact.label}</span>
              <b className="mono">{String(fact.value)}</b>
            </div>
          ))}
        </DrawerSection>
      )}
      <DrawerSection title={`Rule explanation · ${alert.rule}`}>
        <p>{alert.ruleDescription}</p>
        <p>{alert.why}</p>
        {alert.factors.map((factor) => (
          <div className="evidence" key={factor.label}>
            <span>{factor.label}</span>
            <b className="mono">
              {factor.points > 0 ? `+${factor.points}` : factor.points}
            </b>
          </div>
        ))}
        <small>
          Priority is a transparent business rule, not a prediction.
        </small>
      </DrawerSection>
      <DrawerSection title="Rule-based next step">
        <p>{alert.recommendation}</p>
      </DrawerSection>
      <DrawerSection title="AI assistance · generated, not verified" ai>
        <button
          className="btn bordo"
          onClick={() => void run()}
          disabled={running}
        >
          {running ? "Asking Gemini…" : "Ask Gemini for a recommendation"}
        </button>
        <div className="ai-output mono" aria-live="polite">
          {!running && !ai && "No recommendation requested."}
          {running && "▸ Sending this alert's facts to the backend…"}
          {ai &&
            (ai.ai_used ? (
              <span className="ai-copy">
                {[ai.summary, ...ai.observations, ...ai.recommendations].join(
                  "\n",
                )}
              </span>
            ) : (
              <span className="ai-copy">
                AI was not used ({ai.ai_error ?? "unknown reason"}).{" "}
                {ai.summary}
              </span>
            ))}
        </div>
      </DrawerSection>
      <DrawerSection title="Human decision">
        {error && (
          <p className="api-state error" role="alert">
            {error}
          </p>
        )}
        {mode === "none" && (
          <div className="button-row">
            <button
              className="btn"
              disabled={busy || alert.review?.decision === "task_created"}
              onClick={() => setMode("task")}
            >
              Create follow-up task
            </button>
            <button
              className="btn outline"
              disabled={busy || alert.review?.decision === "acknowledged"}
              onClick={() =>
                void act(
                  () =>
                    api.alerts.review(alert.id, { decision: "acknowledged" }),
                  "Alert acknowledged.",
                )
              }
            >
              Acknowledge
            </button>
            <button
              className="btn outline"
              disabled={busy}
              onClick={() => setMode("defer")}
            >
              Defer
            </button>
            <button
              className="btn outline"
              disabled={busy}
              onClick={() => setMode("dismiss")}
            >
              Dismiss
            </button>
            {alert.review && (
              <button
                className="btn outline"
                disabled={busy}
                onClick={() =>
                  void act(
                    () => api.alerts.clearReview(alert.id),
                    "Review cleared; the alert is open again.",
                  )
                }
              >
                Reopen
              </button>
            )}
          </div>
        )}
        {mode !== "none" && (
          <form className="drawer-form" onSubmit={submit} noValidate>
            {mode === "task" && (
              <>
                <label>
                  Assign to
                  <input
                    value={owner}
                    onChange={(event) => {
                      setOwner(event.target.value);
                      setError("");
                    }}
                    maxLength={120}
                    autoFocus
                  />
                </label>
                <label>
                  Due date (optional)
                  <input
                    type="date"
                    value={due}
                    onChange={(event) => setDue(event.target.value)}
                  />
                </label>
              </>
            )}
            {mode === "defer" && (
              <label>
                Bring back on
                <input
                  type="date"
                  min={minDefer}
                  value={deferUntil}
                  onChange={(event) => {
                    setDeferUntil(event.target.value);
                    setError("");
                  }}
                  autoFocus
                />
              </label>
            )}
            {mode === "dismiss" && (
              <label>
                Reason for dismissing
                <textarea
                  rows={2}
                  maxLength={500}
                  value={reason}
                  onChange={(event) => {
                    setReason(event.target.value);
                    setError("");
                  }}
                  autoFocus
                />
              </label>
            )}
            <div className="button-row">
              <button className="btn" type="submit" disabled={busy}>
                {busy
                  ? "Saving…"
                  : mode === "task"
                    ? "Create task"
                    : mode === "defer"
                      ? "Defer alert"
                      : "Dismiss alert"}
              </button>
              <button
                className="btn outline"
                type="button"
                disabled={busy}
                onClick={() => {
                  setMode("none");
                  setError("");
                }}
              >
                Back
              </button>
            </div>
          </form>
        )}
      </DrawerSection>
    </div>
  );
}
function DrawerSection({
  title,
  children,
  ai = false,
}: {
  title: string;
  children: ReactNode;
  ai?: boolean;
}) {
  return (
    <section className={`drawer-section${ai ? " ai" : ""}`}>
      <h4>{title}</h4>
      {children}
    </section>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/auth" element={<Auth />} />
      <Route
        path="*"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      />
    </Routes>
  );
}
