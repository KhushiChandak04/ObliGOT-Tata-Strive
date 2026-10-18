import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import Dialog from "../components/ui/Dialog";
import AgreementForm from "../features/agreements/AgreementForm";
import PartnerForm from "../features/partners/PartnerForm";
import OpportunityForm from "../features/pipeline/OpportunityForm";
import MilestoneForm from "../features/projects/MilestoneForm";
import ProjectForm from "../features/projects/ProjectForm";
import { isWebLink } from "../lib/agreements";
import { EnumLabel, EnumOptions, OptionsProvider, useEnum, useLabel } from "../lib/options";
import { api } from "../services/functions.service";
import { useResource } from "../lib/useResource";
import { todaysAlerts } from "../lib/alerts";
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
  Agreement,
  Alert as ApiAlert,
  AlertEvidence,
  AlertsResponse,
  AnalyzeResponse,
  ClauseProposal,
  CurrencyAmount,
  DashboardSummary,
  DocumentEvidence,
  DocumentReview,
  FinancialTermProposal,
  ImportCommitResult,
  Money,
  ServicingCount,
  TimelinessResponse,
  TimelinessRow,
  TimelinessSummaryRow,
  ImportPreview,
  Milestone,
  ObligationProposal,
  Opportunity,
  OpportunityStage,
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
  recordTitle: string;
  priority: "High" | "Medium" | "Low";
  score: number;
  factors: { label: string; points: number }[];
  urgency?: number;
  impact?: number;
  days: number | null;
  owner: string;
  category: string;
  facts: AlertEvidence[];
  computed: AlertEvidence[];
  why: string;
  recommendation: string;
  review: ApiAlert["review"];
  demo: boolean;
  categoryKey: string;
  tier: string | null;
  group: string | null;
  location: string | null;
};

const toViewAlert = (
  alert: ApiAlert,
  partnerName: (id: string) => string | undefined,
  categoryLabel: (category: string) => string,
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
  recordTitle: alert.record_title,
  priority:
    alert.priority.level === "high"
      ? "High"
      : alert.priority.level === "medium"
        ? "Medium"
        : "Low",
  score: alert.priority.score,
  factors: alert.priority.factors,
  urgency: alert.priority.urgency,
  impact: alert.priority.impact,
  days: alert.days_remaining ?? null,
  owner: alert.owner,
  category: categoryLabel(alert.category),
  facts: alert.evidence.filter((e) => e.source === "record"),
  computed: alert.evidence.filter((e) => e.source === "computed"),
  why: alert.why_it_matters,
  recommendation: alert.recommended_action,
  review: alert.review,
  demo: alert.source_label === "demo",
  categoryKey: alert.category,
  tier: alert.partner_tier ?? null,
  group: alert.partner_group ?? null,
  location: alert.partner_location ?? null,
});

/** Quick filters shared by Action Center, Partners, Agreements and Projects: name, tier, group, location. */
type QuickFilter = { q: string; tier: string; group: string; location: string };
const NO_FILTER: QuickFilter = { q: "", tier: "", group: "", location: "" };

function matchesQuick(f: QuickFilter, item: { text: string; tier?: string | null; group?: string | null; location?: string | null }): boolean {
  return (!f.q || item.text.toLowerCase().includes(f.q.trim().toLowerCase()))
    && (!f.tier || (f.tier === "none" ? !item.tier : item.tier === f.tier))
    && (!f.group || item.group === f.group)
    && (!f.location || (item.location ?? "").toLowerCase() === f.location.toLowerCase());
}

function QuickFilters({ value, onChange, locations, children }: {
  value: QuickFilter; onChange: (next: QuickFilter) => void; locations: (string | null | undefined)[]; children?: ReactNode;
}) {
  const label = useLabel();
  const tiers = useEnum("partner_tier");
  const groups = useEnum("partner_group");
  const places = Array.from(new Set(locations.filter((l): l is string => !!l))).sort();
  const set = (key: keyof QuickFilter) => (event: { target: { value: string } }) => onChange({ ...value, [key]: event.target.value });
  const active = Object.values(value).some(Boolean);
  return (
    <div className="toolbar quick-filters">
      <input className="search" placeholder="Search name" value={value.q} onChange={set("q")} aria-label="Search by name" />
      <select value={value.tier} onChange={set("tier")} aria-label="Filter by tier">
        <option value="">All tiers</option>
        {tiers.map((t) => <option key={t} value={t}>{label("partner_tier", t)}</option>)}
        <option value="none">Tier not set</option>
      </select>
      <select value={value.group} onChange={set("group")} aria-label="Filter by group">
        <option value="">Tata and non-Tata</option>
        {groups.map((g) => <option key={g} value={g}>{label("partner_group", g)}</option>)}
      </select>
      <select value={value.location} onChange={set("location")} aria-label="Filter by location">
        <option value="">All locations</option>
        {places.map((l) => <option key={l} value={l}>{l}</option>)}
      </select>
      {children}
      {active && <button className="text-button" onClick={() => onChange(NO_FILTER)}>Clear filters</button>}
    </div>
  );
}

function TierBadge({ tier }: { tier?: string | null }) {
  const label = useLabel();
  return tier && tier !== "standard" ? <span className={`pill tier-${tier}`}>{label("partner_tier", tier)}</span> : null;
}

/** Short timing label from the backend's days_remaining; the browser does no deadline arithmetic. */
const timing = (alert: Alert) =>
  alert.days === null
    ? "No date"
    : alert.days < 0
      ? `${Math.abs(alert.days)}d overdue`
      : alert.days === 0
        ? "Today"
        : `in ${alert.days}d`;
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
  // How the pipeline works, step by step (an illustration, not live data).
  const lines = [
    "▸ Reading each MOU page (text layer or scan)…",
    "✓ Values extracted with page and quote",
    "  dates, amounts, deadlines, schedules",
    "▸ Checking quotes, dates, and totals…",
    "⚠ Unclear values are highlighted with source pages",
    "✓ Export an editable workbook with evidence",
    "▸ Gemini explains the alert…",
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
            <b>how ObliGOT works</b>
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
            tag="GROQ"
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
  const previousPath = useRef(location.pathname);
  const logOut = async () => {
    if (firebaseAuth) await signOut(firebaseAuth);
    navigate("/");
  };
  const runtime = useResource(() => api.health(), []);
  const [runtimeMode, setRuntimeMode] = useState<string | null>(null);
  useEffect(() => {
    if (runtime.data?.database) setRuntimeMode(runtime.data.database);
  }, [runtime.data?.database]);
  useEffect(() => {
    const updateMode = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      if (detail) setRuntimeMode(detail);
    };
    window.addEventListener("obligot:storage-mode", updateMode);
    return () => window.removeEventListener("obligot:storage-mode", updateMode);
  }, []);
  const workspace = useResource(async () => {
    const [alerts, partners, summary] = await Promise.all([
      api.alerts.list(),
      api.partners.list(),
      api.dashboardSummary(),
    ]);
    return { alerts, partners, summary };
  }, []);
  useEffect(() => {
    // Alerts are computed from current records, so refetch on every page change.
    if (previousPath.current !== location.pathname) workspace.reload();
    previousPath.current = location.pathname;
  }, [location.pathname, workspace.reload]);
  useEffect(() => {
    // Keep alerts live without a manual refresh: poll while the tab is visible and refetch on return.
    // The backend serves these from its Firestore read cache, so polling costs almost no Firestore reads.
    const refresh = () => { if (document.visibilityState === "visible") workspace.reload(); };
    const timer = window.setInterval(refresh, 20000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [workspace.reload]);
  // Live records only. While loading or when the API fails, pages show loading/error states — never sample data.
  const live = workspace.data;
  const livePartners = live?.partners ?? [];
  const label = useLabel();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const names = new Map(livePartners.map((p) => [p.id, p.name]));
  const apiAlerts = live?.alerts.alerts ?? [];
  const sorted = apiAlerts.map((alert) =>
    toViewAlert(alert, (id) => names.get(id), (c) => label("alert_category", c)),
  ); // already ordered by priority score
  const today = todaysAlerts(apiAlerts).map((alert) =>
    toViewAlert(alert, (id) => names.get(id), (c) => label("alert_category", c)),
  );
  const open = sorted;
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
        : page === "/dashboard"
          ? "Good day, team."
          : page === "/pipeline"
            ? "Pipeline"
            : page === "/partners"
            ? "Partners"
            : page === "/agreements"
              ? "Agreements"
              : page === "/projects"
                ? "Projects"
                : page === "/reports"
                  ? "Reports & UCs"
                  : "Import";
  const eyebrow =
    page === "/dashboard"
      ? `Portfolio overview${workspace.data ? ` · rules evaluated ${formatDate(workspace.data.alerts.as_of)}` : ""}`
      : page === "/documents" || page.startsWith("/documents/")
        ? "MOU and addendum intake"
        : page === "/action-center"
          ? "Live rule alerts"
          : ["/pipeline", "/partners", "/agreements", "/projects"].includes(page)
            ? "Live records"
            : runtimeMode === "demo-memory-fallback"
              ? "Synthetic demo data"
              : "Live records";
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
            { to: "/pipeline", label: "Pipeline" },
            { to: "/partners", label: "Partners" },
            { to: "/agreements", label: "Agreements" },
            { to: "/projects", label: "Projects" },
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
      </aside>
      <main className="app-main">
        {runtimeMode === "demo-memory-fallback" && (
          <div className="api-state demo-banner" role="status">
            <b>DEMO MODE — SYNTHETIC DATA — NOT CONNECTED TO LIVE FIRESTORE RECORDS</b>
            <span>Changes are held in backend memory and reset when the backend restarts.</span>
          </div>
        )}
        {runtimeMode === "firestore" && (
          <div className="api-state live-banner" role="status">
            LIVE FIRESTORE MODE — this identifies the configured data source, not its current availability.
          </div>
        )}
        {runtime.error && (
          <div className="api-state error" role="alert">
            <b>LIVE DATA STATUS UNAVAILABLE</b>
            <span>{runtime.error.message}</span>
            <button className="btn small-btn" onClick={runtime.reload}>Retry status</button>
          </div>
        )}
        <div className="page-header">
          <span className="eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
        </div>
        {usesApi && workspace.error && (
          <div className="api-state error" role="alert">
            <b>Could not load workspace data.</b>
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
            sorted={today}
            onSelect={select}
            summary={live.summary}
            onRefresh={workspace.reload}
            refreshing={workspace.loading}
          />
        )}
        {page === "/action-center" && live && (
          <ActionCenter
            open={open}
            sorted={sorted}
            hidden={live.alerts.counts.hidden_by_review}
            onSelect={select}
          />
        )}
        {page === "/documents" && (
          <DocumentsPage partners={livePartners} />
        )}
        {page.startsWith("/documents/") && (
          <DocumentReviewPage partners={livePartners} />
        )}
        {page === "/pipeline" && <PipelinePage onChanged={workspace.reload} />}
        {page === "/partners" && <PartnersPage onChanged={workspace.reload} />}
        {page === "/agreements" && (
          <AgreementsPage onChanged={workspace.reload} />
        )}
        {page === "/projects" && <ProjectsPage onChanged={workspace.reload} />}
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
        <b>{alert.partner} · {alert.recordTitle} <TierBadge tier={alert.tier} /></b>
        <small>
          {alert.ruleTitle} · {alert.owner}
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
  sorted,
  onSelect,
  summary,
  onRefresh,
  refreshing,
}: {
  sorted: Alert[];
  onSelect: (alert: Alert) => void;
  summary: DashboardSummary;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  // Every figure below is computed by the backend from current records (GET /api/dashboard/summary).
  const label = useLabel();
  const families = Object.entries(summary.alerts.by_category).map(
    ([name, count]) => [label("alert_category", name), count] as const,
  );
  const max = Math.max(1, ...families.map(([, count]) => count));
  const money = (rows: CurrencyAmount[]) =>
    rows.map((r) =>
      `${formatAmount(r.amount, r.currency)} (${r.count})`,
    ).join(" · ");
  const coverage = summary.coverage.state.length ? summary.coverage.state : summary.coverage.location;
  return (
    <>
      <div className="kpis">
        <Kpi value={summary.alerts.open} label="Open alerts" />
        <Kpi value={summary.alerts.overdue} label="Overdue items" hot />
        <Kpi value={summary.alerts.mous_expiring_30d} label="MOUs expiring ≤30d" />
        <Kpi value={summary.tasks.open} label="Open follow-ups" />
      </div>
      <div className="document-strip">
        <span>
          <b>{summary.documents.awaiting_review}</b> Documents extracted
        </span>
        <span>
          <b>{summary.documents.needs_attention}</b> Extraction failures / retry
        </span>
        <span>
          <b>{summary.documents.addenda_awaiting_review}</b> Addenda extracted
        </span>
      </div>
      <div className="grid2">
        <section className="box">
          <div className="dashboard-heading">
            <div>
              <h3>Priority alerts</h3>
              <p>Up to five active alerts without a follow-up, highest priority first.</p>
            </div>
            <button className="btn small-btn" onClick={onRefresh} disabled={refreshing}>
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
          </div>
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
      <div className="grid2">
        <section className="box">
          <h3>Money to follow up</h3>
          <div className="detail-row">
            <span>Contractual releases overdue</span>
            <span>{summary.finance.fund_releases_overdue.length ? money(summary.finance.fund_releases_overdue) : "None recorded"}</span>
          </div>
          <div className="detail-row">
            <span>Contractual releases not yet received</span>
            <span>{summary.finance.fund_releases_due.length ? money(summary.finance.fund_releases_due) : "None recorded"}</span>
          </div>
          <div className="detail-row">
            <span>Unpaid invoices</span>
            <span>{summary.finance.unpaid_invoices.length ? money(summary.finance.unpaid_invoices) : "None recorded"}</span>
          </div>
          <small>Totals are per currency and per kind; they are never combined.</small>
        </section>
        <section className="box">
          <h3>Reporting</h3>
          <div className="detail-row"><span>Overdue reports and UCs</span><span>{summary.reporting.overdue}</span></div>
          <div className="detail-row"><span>Open reports</span><span>{summary.reporting.open_reports}</span></div>
          <div className="detail-row"><span>UCs pending</span><span>{summary.reporting.pending_ucs}</span></div>
          {coverage.length > 0 && (
            <>
              <h3>Coverage in approved agreements</h3>
              {coverage.map((c) => (
                <div className="detail-row" key={c.label}><span>{c.label}</span><span>{c.count}</span></div>
              ))}
            </>
          )}
        </section>
      </div>
      <CashflowTable />
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
  hidden,
  onSelect,
}: {
  open: Alert[];
  sorted: Alert[];
  hidden: number;
  onSelect: (alert: Alert) => void;
}) {
  const [filter, setFilter] = useState<QuickFilter>(NO_FILTER);
  const [level, setLevel] = useState("");
  const [category, setCategory] = useState("");
  const label = useLabel();
  const categories = useEnum("alert_category");
  const shown = sorted.filter((a) => matchesQuick(filter, { text: `${a.partner} ${a.recordTitle} ${a.ruleTitle} ${a.owner}`, ...a })
    && (!level || a.priority === level) && (!category || a.categoryKey === category));
  return (
    <>
      <section className="box">
        <h3>All outstanding ({shown.length === open.length ? open.length : `${shown.length} of ${open.length}`})</h3>
        <QuickFilters value={filter} onChange={(f) => { setFilter(f); if (!Object.values(f).some(Boolean)) { setLevel(""); setCategory(""); } }}
          locations={sorted.map((a) => a.location)}>
          <select value={level} onChange={(e) => setLevel(e.target.value)} aria-label="Filter by priority">
            <option value="">All priorities</option>
            {["High", "Medium", "Low"].map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category">
            <option value="">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{label("alert_category", c)}</option>)}
          </select>
        </QuickFilters>
        {hidden > 0 && (
          <small>
            {hidden} deferred or dismissed alert{hidden === 1 ? " is" : "s are"}{" "}
            hidden until the date passes or the record changes.
          </small>
        )}
        {shown.map((alert, index) => (
          <AlertRow
            key={alert.id}
            alert={alert}
            index={index}
            onSelect={onSelect}
          />
        ))}
        {!shown.length && <p>{sorted.length ? "No alerts match these filters." : "No open alerts."}</p>}
      </section>
    </>
  );
}
const formatDate = (value: string | null): string =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(new Date(value))
    : "Not recorded";
function TableState({ message }: { message: string }) {
  return <p className="table-state">{message}</p>;
}
function PipelinePage({ onChanged }: { onChanged: () => void }) {
  const data = useResource(async () => {
    const [opportunities, partners, documents] = await Promise.all([
      api.opportunities.list(),
      api.partners.list(),
      api.documents.list(),
    ]);
    return { opportunities, partners, documents };
  }, []);
  const [dialog, setDialog] = useState<{ opportunity?: Opportunity } | null>(
    null,
  );
  const [message, setMessage] = useState("");
  const names = new Map((data.data?.partners ?? []).map((p) => [p.id, p.name]));
  const files = new Map((data.data?.documents ?? []).map((d) => [d.id, d.filename]));
  const origin = (item: Opportunity) => item.source_document_id
    ? <Link to={`/documents/${item.source_document_id}`}>From MOU: {files.get(item.source_document_id) ?? "open document"}</Link>
    : <span>Manual entry</span>;
  const label = useLabel();
  const stages = useEnum("opportunity_stage") as OpportunityStage[];
  const stageName = (stage: string) => label("opportunity_stage", stage);
  const [view, setView] = useState<"board" | "table">(() => {
    try { return window.localStorage.getItem(PIPELINE_VIEW_KEY) === "table" ? "table" : "board"; } catch { return "board"; }
  });
  const chooseView = (next: "board" | "table") => {
    setView(next);
    try { window.localStorage.setItem(PIPELINE_VIEW_KEY, next); } catch { /* storage unavailable: view is not remembered */ }
  };
  const [moving, setMoving] = useState<string | null>(null);
  const refresh = (text: string) => {
    setDialog(null);
    setMessage(text);
    data.reload();
    onChanged();
  };
  const logFollowup = async (item: Opportunity) => {
    setMoving(item.id);
    setMessage("");
    try {
      // The browser's local date; the backend re-evaluates follow-up alerts from it on the next refresh.
      const today = new Date();
      const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
      await api.opportunities.update(item.id, { last_followup_date: iso });
      refresh(`Recorded a follow-up today on “${item.title}”. Set the next step with Edit.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not record the follow-up.");
    } finally {
      setMoving(null);
    }
  };
  const move = async (item: Opportunity, next: OpportunityStage) => {
    setMoving(item.id);
    setMessage("");
    try {
      await api.opportunities.update(item.id, { stage: next });
      refresh(`Moved “${item.title}” to ${stageName(next)}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not move the deal.");
    } finally {
      setMoving(null);
    }
  };
  return (
    <>
      <RegisterState
        resource={data}
        label="opportunities"
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
        <>
          <p className="muted-copy">
            Stages record confirmed business progress. Update them when the
            opportunity’s status actually changes. An MOU becomes operational only once its deal reaches Approval.
          </p>
          <PipelineTotals opportunities={data.data.opportunities} />
          <div className="tabs view-toggle" role="group" aria-label="Pipeline view">
            <button className={view === "board" ? "active" : ""} aria-pressed={view === "board"} onClick={() => chooseView("board")}>Board</button>
            <button className={view === "table" ? "active" : ""} aria-pressed={view === "table"} onClick={() => chooseView("table")}>Table</button>
          </div>
          {view === "board" ? (
            <div className="pipeline-grid">
              {stages.map((stage) => {
                const column = data.data!.opportunities.filter((item) => item.stage === stage);
                const inr = column.reduce((sum, item) => sum + ((item.currency ?? "INR") === "INR" ? item.amount ?? 0 : 0), 0);
                return (
                  <section className="pipeline-column" key={stage}>
                    <h3>{stageName(stage)}<span className="pill">{column.length}</span></h3>
                    {inr > 0 && <small className="pipeline-sum">{formatMoney(inr, "INR")}</small>}
                    {column.length ? column.map((item) => {
                      const followup = item.last_followup_date ? daysSince(item.last_followup_date) : null;
                      return (
                        <div className="pipeline-card" key={item.id}>
                          <b>{names.get(item.partner_id) ?? item.partner_id}</b>
                          <small>{item.title}</small>
                          <dl className="pipeline-fields">
                            <dt>Amount</dt><dd>{item.amount != null ? formatMoney(item.amount, item.currency) : "—"}</dd>
                            <dt>Sanction</dt><dd>{item.sanction_probability != null ? `${item.sanction_probability}%` : "—"}</dd>
                            <dt>Location</dt><dd>{item.location || "—"}</dd>
                            <dt>Owner</dt><dd>{item.owner}</dd>
                            <dt>Started</dt><dd>{item.started_on ? `${formatDate(item.started_on)} (${daysSince(item.started_on)} d)` : "—"}</dd>
                            <dt>Follow-up</dt>
                            <dd className={followup !== null && followup > STALE_FOLLOWUP_DAYS ? "text-bordo" : ""}>
                              {item.last_followup_date ? `${formatDate(item.last_followup_date)} (${followup} d ago)` : "—"}
                            </dd>
                            <dt>Next step</dt><dd>{item.next_step || "—"}{item.next_step_date ? ` · ${formatDate(item.next_step_date)}` : ""}</dd>
                            <dt>Source</dt><dd>{origin(item)}</dd>
                          </dl>
                          <div className="button-row">
                            <select aria-label={`Stage of ${item.title}`} value={item.stage} disabled={moving !== null}
                              onChange={(event) => void move(item, event.target.value as OpportunityStage)}>
                              {stages.map((s) => <option key={s} value={s}>{stageName(s)}</option>)}
                            </select>
                            <button className="text-button" onClick={() => void logFollowup(item)} disabled={moving !== null}>Followed up today</button>
                            <button className="text-button" onClick={() => setDialog({ opportunity: item })} aria-label={`Edit ${item.title}`}>Edit</button>
                          </div>
                        </div>
                      );
                    }) : <TableState message="No deals" />}
                  </section>
                );
              })}
            </div>
          ) : (
          <DataTable
            headers={["Partner", "Opportunity", "Source", "Location", "Amount", "Sanction %", "Stage", "Started", "Last follow-up", "Owner", "Next step", "Next step date", ""]}
            rows={data.data.opportunities.map((item) => [
              names.get(item.partner_id) ?? item.partner_id,
              item.title,
              origin(item),
              item.location || "—",
              item.amount != null ? formatMoney(item.amount, item.currency) : "—",
              item.sanction_probability != null ? `${item.sanction_probability}%` : "—",
              stageName(item.stage),
              item.started_on ? `${formatDate(item.started_on)} (${daysSince(item.started_on)} days)` : "—",
              item.last_followup_date ? `${formatDate(item.last_followup_date)} (${daysSince(item.last_followup_date)} days ago)` : "—",
              item.owner,
              item.next_step || "Not recorded",
              formatDate(item.next_step_date ?? null),
              <button
                className="text-button"
                onClick={() => setDialog({ opportunity: item })}
                aria-label={`Edit ${item.title}`}
              >
                Edit
              </button>,
            ])}
            empty="No opportunities recorded yet."
          />
          )}
        </>
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

const PIPELINE_VIEW_KEY = "obligot.pipelineView";
// Matches the backend's default stale_opportunity_days rule threshold.
const STALE_FOLLOWUP_DAYS = 30;

function daysSince(isoDate: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(`${isoDate}T00:00:00`).getTime()) / 86_400_000));
}

function formatMoney(amount: number, currency = "INR"): string {
  try {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString("en-IN")}`;
  }
}

/** Open pipeline at a glance. Amounts are summed per currency only; probability-weighted value uses the team's own %. */
function PipelineTotals({ opportunities }: { opportunities: Opportunity[] }) {
  const open = opportunities.filter((o) => o.stage !== "closed" && o.stage !== "active");
  const funders = new Set(open.map((o) => o.partner_id)).size;
  const byCurrency = new Map<string, { total: number; weighted: number }>();
  for (const o of open) {
    if (o.amount == null) continue;
    const entry = byCurrency.get(o.currency ?? "INR") ?? { total: 0, weighted: 0 };
    entry.total += o.amount;
    if (o.sanction_probability != null) entry.weighted += (o.amount * o.sanction_probability) / 100;
    byCurrency.set(o.currency ?? "INR", entry);
  }
  return (
    <div className="button-row">
      <span className="pill">Open deals · {open.length}</span>
      <span className="pill">Funders · {funders}</span>
      {[...byCurrency].map(([currency, v]) => (
        <span className="pill" key={currency}>
          Pipeline · {formatMoney(v.total, currency)} (weighted {formatMoney(v.weighted, currency)})
        </span>
      ))}
    </div>
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

/** Amounts per currency, side by side; never added across currencies. */
function moneyText(money: Money): string {
  const parts = Object.entries(money).map(([currency, amount]) => formatMoney(amount, currency));
  return parts.length ? parts.join(" · ") : "—";
}

/** "3/5 done", with overdue and missing evidence called out. */
function Servicing({ count }: { count: ServicingCount }) {
  if (!count.total) return <span className="muted-copy">None</span>;
  return (
    <span>
      {count.done}/{count.total} done
      {count.overdue > 0 && <b className="text-bordo"> · {count.overdue} overdue</b>}
      {count.no_evidence > 0 && <small className="text-bordo"> · {count.no_evidence} without evidence</small>}
    </span>
  );
}

/** Every signed MOU on one screen: who, how much, money in, servicing, and what is due next. */
function MouSummary() {
  const data = useResource(() => api.portfolio(), []);
  const [filter, setFilter] = useState<QuickFilter>(NO_FILTER);
  const label = useLabel();
  const rows = (data.data?.mous ?? []).filter((m) => matchesQuick(filter, { text: `${m.partner_name ?? ""} ${m.title ?? ""} ${m.owner ?? ""}`, ...m }));
  return (
    <section className="box">
      <h3>Signed MOUs — summary <small>{data.data ? `${data.data.mous.length} MOUs · as of ${formatDate(data.data.as_of)}` : ""}</small></h3>
      {data.error && <p className="api-state error" role="alert">{data.error.message} <button className="btn small-btn" onClick={data.reload}>Retry</button></p>}
      {data.loading && !data.data && <p className="api-state" role="status">Loading MOU summary…</p>}
      {data.data && (
        <>
          <QuickFilters value={filter} onChange={setFilter} locations={data.data.mous.map((m) => m.location)} />
          <DataTable
            headers={["Funder", "MOU", "Period", "Committed", "Received", "Reports", "UCs", "Deliverables", "Next due"]}
            rows={rows.map((m) => [
              <span key="f">{m.partner_name ?? "—"} <TierBadge tier={m.tier} />{m.group && <small> · {label("partner_group", m.group)}</small>}{m.location && <small> · {m.location}</small>}</span>,
              m.source_document_id ? <Link key="t" to={`/documents/${m.source_document_id}`}>{m.title}</Link> : m.title ?? "—",
              `${m.start_date ? formatDate(m.start_date) : "?"} – ${m.expiry_date ? formatDate(m.expiry_date) : "no end date"}`,
              moneyText(m.committed),
              moneyText(m.received),
              <Servicing key="r" count={m.reports} />,
              <Servicing key="u" count={m.ucs} />,
              <Servicing key="m" count={m.milestones} />,
              m.next_deadline ? `${formatDate(m.next_deadline.date)} · ${m.next_deadline.kind}` : "Nothing dated",
            ])}
            empty={data.data.mous.length ? "No MOUs match these filters." : "No signed MOUs yet. Create records from an MOU on the Documents page."}
          />
        </>
      )}
    </section>
  );
}

/** Expected (dated payment terms) vs received (recorded receipts), month by month, per currency. */
function CashflowTable() {
  const data = useResource(() => api.portfolio(), []);
  if (data.error) return <section className="box"><p className="api-state error" role="alert">{data.error.message} <button className="btn small-btn" onClick={data.reload}>Retry</button></p></section>;
  if (!data.data) return <section className="box"><p className="api-state" role="status">Loading cashflow…</p></section>;
  const month = (key: string) => new Intl.DateTimeFormat("en-IN", { month: "short", year: "numeric" }).format(new Date(`${key}-01T00:00:00`));
  const current = data.data.as_of.slice(0, 7);
  return (
    <section className="box">
      <h3>Cashflow by month <small>expected from MOU payment terms vs received</small></h3>
      <DataTable
        headers={["Month", "Expected", "Received", "Gap"]}
        rows={data.data.cashflow.map((c) => [
          <span key="m">{month(c.month)}{c.month === current ? " (this month)" : ""}</span>,
          c.expected ? formatMoney(c.expected, c.currency) : "—",
          c.received ? formatMoney(c.received, c.currency) : "—",
          c.expected > c.received && c.month <= current
            ? <b key="g" className="text-bordo">{formatMoney(c.expected - c.received, c.currency)} not received</b>
            : c.expected > c.received ? `${formatMoney(c.expected - c.received, c.currency)} to come` : "—",
        ])}
        empty="No dated payment terms or receipts yet."
      />
      {Object.keys(data.data.unscheduled_expected).length > 0 && (
        <small>Also expected, with no date in the MOU: {moneyText(data.data.unscheduled_expected)}.</small>
      )}
    </section>
  );
}

const TIER_ORDER: Record<string, number> = { platinum: 0, gold: 1, silver: 2, standard: 3 };

/** Every funder at a glance: tier, group, location, money, and how their MOUs are being serviced. */
function PartnersPage({ onChanged }: { onChanged: () => void }) {
  const data = useResource(async () => {
    const [partners, portfolio] = await Promise.all([api.partners.list(), api.portfolio()]);
    return { partners, portfolio };
  }, []);
  const [filter, setFilter] = useState<QuickFilter>(NO_FILTER);
  const [dialog, setDialog] = useState<{ partner?: Partner } | null>(null);
  const [message, setMessage] = useState("");
  const label = useLabel();
  const servicing = new Map((data.data?.portfolio.funders ?? []).map((f) => [f.partner_id, f]));
  const none: ServicingCount = { total: 0, done: 0, overdue: 0, no_evidence: 0 };
  const rows = (data.data?.partners ?? [])
    .filter((p) => matchesQuick(filter, { text: `${p.name} ${p.owner} ${p.category}`, ...p }))
    .sort((a, b) => (TIER_ORDER[a.tier ?? ""] ?? 9) - (TIER_ORDER[b.tier ?? ""] ?? 9) || a.name.localeCompare(b.name));
  const refresh = (text: string) => { setDialog(null); setMessage(text); data.reload(); onChanged(); };
  return (
    <>
      <RegisterState resource={data} label="partners" message={message}
        action={<button className="btn small-btn" onClick={() => setDialog({})} disabled={!data.data}>Add partner</button>} />
      {data.data && (
        <section className="box">
          <p className="muted-copy">Set each funder's tier and group here (or import your customer sheet on the Import page). Platinum and Gold partners' alerts rank higher.</p>
          <QuickFilters value={filter} onChange={setFilter} locations={data.data.partners.map((p) => p.location)} />
          <DataTable
            headers={["Partner", "Tier", "Group", "Location", "Owner", "MOUs", "Committed", "Received", "Reports", "UCs", "Deliverables", ""]}
            rows={rows.map((p) => {
              const f = servicing.get(p.id);
              return [
                p.name,
                p.tier ? label("partner_tier", p.tier) : "Not set",
                p.group ? label("partner_group", p.group) : "Not set",
                p.location || "—",
                p.owner,
                f?.mous ?? 0,
                f ? moneyText(f.committed) : "—",
                f ? moneyText(f.received) : "—",
                <Servicing key="r" count={f?.reports ?? none} />,
                <Servicing key="u" count={f?.ucs ?? none} />,
                <Servicing key="m" count={f?.milestones ?? none} />,
                <button key="e" className="text-button" onClick={() => setDialog({ partner: p })} aria-label={`Edit ${p.name}`}>Edit</button>,
              ];
            })}
            empty={data.data.partners.length ? "No partners match these filters." : "No partners yet."}
          />
        </section>
      )}
      <Dialog open={dialog !== null} title={dialog?.partner ? "Edit partner" : "Add partner"} onClose={() => setDialog(null)}>
        {dialog && <PartnerForm partner={dialog.partner} onCancel={() => setDialog(null)} onSaved={(saved) => refresh(`Saved “${saved.name}”.`)} />}
      </Dialog>
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
          <MouSummary />
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
                <EnumOptions group="agreement_status" />
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
                  <EnumLabel group="agreement_status" value={a.status} />
                </span>,
                formatDate(a.start_date ?? null),
                formatDate(a.expiry_date ?? null),
                <EnumLabel key="signed" group="signed_copy" value={a.signed_copy} />,
                a.owner,
                <EnumLabel key="renewal" group="renewal_status" value={a.renewal_status} />,
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
    const [projects, milestones, partners, portfolio] = await Promise.all([
      api.projects.list(),
      api.milestones.list(),
      api.partners.list(),
      api.portfolio(),
    ]);
    return { projects, milestones, partners, portfolio };
  }, []);
  const [filter, setFilter] = useState<QuickFilter>(NO_FILTER);
  const [projectStatus, setProjectStatus] = useState("");
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
  const partnerOf = new Map((data.data?.partners ?? []).map((p) => [p.id, p]));
  const mouOf = new Map((data.data?.portfolio.mous ?? []).filter((m) => m.project_id).map((m) => [m.project_id!, m]));
  const visible = (data.data?.projects ?? []).filter((project) => {
    const partner = project.partner_id ? partnerOf.get(project.partner_id) : undefined;
    return matchesQuick(filter, { text: `${project.name} ${partner?.name ?? ""} ${project.owner}`, tier: partner?.tier,
      group: partner?.group, location: partner?.location }) && (!projectStatus || project.status === projectStatus);
  });
  const refresh = (text: string) => {
    setDialog(null);
    setMessage(text);
    data.reload();
    onChanged();
  };
  const label = useLabel();
  const milestoneStatus = (status: Milestone["status"]) =>
    label("milestone_status", status);
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
      {data.data && data.data.projects.length > 0 && (
        <QuickFilters value={filter} onChange={setFilter} locations={data.data.partners.map((p) => p.location)}>
          <select value={projectStatus} onChange={(e) => setProjectStatus(e.target.value)} aria-label="Filter by project status">
            <option value="">All statuses</option>
            <EnumOptions group="project_status" />
          </select>
        </QuickFilters>
      )}
      {data.data &&
        (visible.length ? (
          <div className="project-grid">
            {visible.map((project) => {
              const partner = project.partner_id ? partnerOf.get(project.partner_id) : undefined;
              const mou = mouOf.get(project.id);
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
                          : "No partner"}{" "}
                        <TierBadge tier={partner?.tier} />
                        {partner?.group && <small> · {label("partner_group", partner.group)}</small>}
                        {partner?.location && <small> · {partner.location}</small>}
                      </p>
                    </div>
                    <span className="pill">
                      {project.status.replace("_", " ")}
                    </span>
                  </div>
                  {mou && (
                    <dl className="pipeline-fields project-glance">
                      <dt>Committed</dt><dd>{moneyText(mou.committed)}</dd>
                      <dt>Received</dt><dd>{moneyText(mou.received)}</dd>
                      <dt>Reports</dt><dd><Servicing count={mou.reports} /></dd>
                      <dt>UCs</dt><dd><Servicing count={mou.ucs} /></dd>
                      <dt>Next due</dt><dd>{mou.next_deadline ? `${formatDate(mou.next_deadline.date)} · ${mou.next_deadline.kind}` : "Nothing dated"}</dd>
                    </dl>
                  )}
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
          <TableState message={data.data.projects.length ? "No projects match these filters." : "No projects recorded yet."} />
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

/** An amount in its own currency; without a valid currency code the number is shown with a note, never as rupees. */
function formatAmount(amount: number, currency?: string | null): string {
  if (currency && /^[A-Z]{3}$/.test(currency)) {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
  }
  return `${new Intl.NumberFormat("en-IN").format(amount)} (currency not recorded)`;
}

type ObligationRow = {
  id: string; kind: "report" | "uc"; type: string; title: string; partnerId: string; dueDate?: string | null;
  status: string; owner: string; evidence: string | null; overdue: boolean; done: boolean; demo: boolean;
};

function ReportsPage() {
  const data = useResource(async () => {
    const [reports, finance, partners, alerts, timeliness] = await Promise.all([
      api.reports.list(), api.finance.list(undefined, { record_type: "utilization_certificate" }), api.partners.list(), api.alerts.list(),
      api.timeliness(),
    ]);
    return { reports, finance, partners, alerts, timeliness };
  }, []);
  const [tab, setTab] = useState("All");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [submittedOn, setSubmittedOn] = useState("");
  const [evidence, setEvidence] = useState("");
  const names = new Map((data.data?.partners ?? []).map((p) => [p.id, p.name]));
  const overdueIds = new Set((data.data?.alerts.alerts ?? []).filter((a) => a.rule_id === "REPORT_OVERDUE" || a.rule_id === "UC_OVERDUE").map((a) => a.record_id));
  const timing = new Map((data.data?.timeliness.rows ?? []).map((r) => [r.id, r]));
  const rows: ObligationRow[] = [
    ...(data.data?.reports ?? []).map((r) => ({
      id: r.id, kind: "report" as const, type: `${r.report_type} report`, title: r.title, partnerId: r.partner_id, dueDate: r.due_date,
      status: r.status, owner: r.owner, evidence: r.evidence ?? null, overdue: overdueIds.has(r.id), done: r.status === "submitted" || r.status === "accepted", demo: r.source_label === "demo",
    })),
    ...(data.data?.finance ?? []).map((f) => ({
      id: f.id, kind: "uc" as const, type: "Utilization certificate", title: f.title, partnerId: f.partner_id, dueDate: f.due_date,
      status: f.status, owner: f.owner ?? "Unassigned", evidence: f.evidence ?? null, overdue: overdueIds.has(f.id), done: ["submitted", "accepted"].includes(f.status), demo: f.source_label === "demo",
    })),
  ];
  const filtered = rows.filter((r) =>
    tab === "All" ? true : tab === "Overdue" ? r.overdue : tab === "Submitted" ? r.done : !r.done && !r.overdue,
  );
  const markSubmitted = async (row: ObligationRow) => {
    setMessage("");
    try {
      if (row.kind === "report") await api.reports.update(row.id, { status: "submitted", submitted_date: submittedOn, evidence: evidence.trim() });
      else await api.finance.update(row.id, { status: "submitted", received_date: submittedOn, evidence: evidence.trim() });
      setMessage(`Marked “${row.title}” submitted.`);
      setSubmitting(null);
      setSubmittedOn("");
      setEvidence("");
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
          headers={["Type", "Title", "Partner", "Owner", "Due", "Done on", "Timeliness", "Evidence", ""]}
          rows={filtered.map((row) => [
            row.type,
            row.title,
            names.get(row.partnerId) ?? row.partnerId,
            row.owner,
            row.dueDate ? formatDate(row.dueDate) : "Due date not recorded",
            timing.get(row.id)?.done_date ? formatDate(timing.get(row.id)!.done_date!) : "—",
            <span className={`pill ${timing.get(row.id)?.state === "overdue" || timing.get(row.id)?.state === "late" ? "high" : ""}`} key="status">
              {timingLabel(timing.get(row.id))}
            </span>,
            row.evidence ? row.evidence : row.done ? <b key="ev" className="text-bordo">No evidence recorded</b> : "—",
            row.done ? (
              ""
            ) : submitting === row.id ? (
              <span className="button-row" key="submit">
                <input type="date" aria-label={row.kind === "uc" ? "Received on" : "Submitted on"} value={submittedOn} onChange={(e) => setSubmittedOn(e.target.value)} />
                <input aria-label="Evidence" placeholder="Evidence: email subject, courier no., portal ref…" value={evidence}
                  onChange={(e) => setEvidence(e.target.value)} maxLength={500} />
                <button className="btn small-btn" disabled={!submittedOn || evidence.trim().length < 3} onClick={() => void markSubmitted(row)}>
                  Save
                </button>
              </span>
            ) : (
              <button
                className="btn outline small-btn"
                key="submit"
                onClick={() => setSubmitting(row.id)}
              >
                Mark submitted
              </button>
            ),
          ])}
          empty="No reports or utilization certificates match this tab."
        />
      )}
      {data.data && <TimelinessSummary data={data.data.timeliness} />}
    </section>
  );
}

function timingLabel(row?: TimelinessRow): string {
  if (!row) return "—";
  if (row.state === "on_time") return row.days === 0 ? "On time" : `On time (${-row.days!} days early)`;
  if (row.state === "late") return `Late by ${row.days} days`;
  if (row.state === "overdue") return `Overdue by ${row.days} days`;
  if (row.state === "pending") return `Due in ${row.days} days`;
  if (row.state === "done_no_due_date") return "Done (no due date)";
  return "No due date";
}

const APPROVED_DEAL_STAGES = ["approval", "agreement", "active", "renewal"];

/** The pipeline deal this MOU represents, built from its extracted values; manual deals are entered on the Pipeline page. */
function MouPipelineDeal({ document, partners }: { document: SourceDocument; partners: Partner[] }) {
  const data = useResource(() => api.documents.pipelineDeal(document.id), [document.id, document.agreement_id]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const add = async () => {
    setBusy(true);
    setError("");
    try { await api.documents.addPipelineDeal(document.id); data.reload(); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not add the deal."); }
    finally { setBusy(false); }
  };
  const deal = data.data?.deal ?? null;
  const shown = deal ?? data.data?.proposed;
  const partnerName = (shown?.partner_id && partners.find((p) => p.id === shown.partner_id)?.name) || "Partner chosen when creating records";
  return (
    <section className="box">
      <h3>Pipeline deal {deal ? <span className="pill">On the pipeline · {deal.stage}</span> : <span className="pill high">Not on the pipeline yet</span>}</h3>
      {data.error && <p className="api-state error" role="alert">{data.error.message} <button className="btn small-btn" onClick={data.reload}>Retry</button></p>}
      {data.loading && !data.data && <p className="api-state" role="status">Loading the deal…</p>}
      {shown && (
        <DataTable
          headers={["Funder", "Deal", "Location", "Amount", "Sanction %", "Started", "Last follow-up"]}
          rows={[[
            partnerName, shown.title ?? "—", shown.location || "Not stated in the MOU",
            shown.amount != null ? formatMoney(shown.amount, shown.currency) : "Not stated in the MOU",
            shown.sanction_probability != null ? `${shown.sanction_probability}%` : "—",
            shown.started_on ? formatDate(shown.started_on) : "Not stated in the MOU",
            shown.last_followup_date ? formatDate(shown.last_followup_date) : "—",
          ]]}
          empty=""
        />
      )}
      {deal ? (
        <p><Link to="/pipeline">Open the pipeline</Link> to edit the stage, sanction % and follow-ups.</p>
      ) : document.agreement_id ? (
        <button className="btn small-btn" disabled={busy} onClick={() => void add()}>{busy ? "Adding…" : "Add to pipeline"}</button>
      ) : (
        <p>These values come from the MOU. The deal is added to the pipeline when you create records below.</p>
      )}
      {error && <p className="api-state error" role="alert">{error}</p>}
    </section>
  );
}

/** Is everything a Tata STRIVE MOU should state actually in this one? Checks the extracted values only; nothing is inferred. */
function MouChecklist({ review, deals, partnerId, dealId }: {
  review: DocumentReview; deals: Opportunity[]; partnerId: string; dealId: string;
}) {
  const field = (name: string) => review.fields.some((f) => f.field === name && f.review_state !== "rejected" && (f.approved_value ?? f.proposed_value) != null && (f.approved_value ?? f.proposed_value) !== "");
  const live = <T extends { review_state?: string }>(rows: T[]) => rows.filter((r) => r.review_state !== "rejected");
  const scope = live(review.programme_scope);
  const terms = live(review.financial_terms);
  const obligations = live(review.obligations);
  const ofType = (...types: string[]) => obligations.filter((o) => types.includes(o.obligation_type));
  const tranches = terms.filter((t) => t.term_type === "tranche" || t.term_type === "payment_term");
  const reports = ofType("progress_report", "impact_report");
  const ucs = ofType("utilization_certificate");
  const dated = (rows: { due_date?: string | null }[]) => rows.filter((r) => r.due_date).length;
  const deal = deals.find((d) => d.id === dealId) ?? deals.find((d) => partnerId && d.partner_id === partnerId);
  const checks: [string, boolean, string][] = [
    ["Partner named", field("partner_name") || field("legal_entity_name"), ""],
    ["Start date", field("effective_date") || field("start_date") || field("execution_date"), ""],
    ["End date or duration", field("expiry_date") || field("duration"), "needed for expiry alerts"],
    ["Target group", scope.some((s) => s.dimension === "beneficiary_group"), "who the programme is for"],
    ["Numeric targets", scope.some((s) => s.dimension === "target" && s.target_value != null),
      scope.filter((s) => s.target_value != null).map((s) => `${s.target_value} ${s.target_unit ?? ""} ${s.value}`.trim()).slice(0, 3).join("; ")],
    ["Locations", scope.some((s) => s.dimension === "state" || s.dimension === "region" || !!s.location), ""],
    ["Deliverables", ofType("deliverable", "milestone").length > 0, `${ofType("deliverable", "milestone").length} found`],
    ["Total budget", terms.some((t) => t.term_type === "total_commitment" || t.term_type === "annual_budget"), ""],
    ["Payment schedule", tranches.length > 0, tranches.length ? `${tranches.length} instalments, ${dated(tranches)} with a date` : ""],
    ["Progress reports", reports.length > 0, reports.length ? `${reports.length} found, ${dated(reports)} with a due date` : ""],
    ["Utilization certificates", ucs.length > 0, ucs.length ? `${ucs.length} found, ${dated(ucs)} with a due date` : ""],
    ["Pipeline deal approved", !!deal && APPROVED_DEAL_STAGES.includes(deal.stage),
      deal ? `“${deal.title}” is at stage ${deal.stage}` : "no pipeline deal for this partner"],
  ];
  const missing = checks.filter(([, ok]) => !ok).length;
  return (
    <section className="box validation">
      <h3>MOU completeness {missing ? <span className="pill high">{missing} missing</span> : <span className="pill">Complete</span>}</h3>
      {checks.map(([name, ok, detail]) => (
        <p key={name}>{ok ? "✓" : "✗"} {name}{detail ? ` — ${detail}` : ""}</p>
      ))}
    </section>
  );
}

/** Due vs actually done: organisation totals and per account owner, separately for reports and UCs. */
function TimelinessSummary({ data }: { data: TimelinessResponse }) {
  const cells = (s: TimelinessSummaryRow) => [
    s.total, s.done, s.on_time, s.late, s.overdue, s.pending,
    s.on_time_rate === null ? "—" : `${s.on_time_rate}%`, s.average_days_late === null ? "—" : `${s.average_days_late} days`,
  ];
  const headers = ["Total", "Done", "On time", "Late", "Overdue", "Pending", "On-time rate", "Avg. delay"];
  return (
    <>
      <h3>Timeliness — organisation (as of {formatDate(data.as_of)})</h3>
      <DataTable
        headers={["", ...headers]}
        rows={[["Progress reports", ...cells(data.organisation.report)], ["Utilization certificates", ...cells(data.organisation.uc)]]}
        empty="No reports or UCs yet."
      />
      <h3>Timeliness — by account owner</h3>
      <DataTable
        headers={["Owner", "Document", ...headers]}
        rows={data.owners.flatMap((o) => ([["report", "Reports"], ["uc", "UCs"]] as const)
          .filter(([kind]) => o[kind].total > 0)
          .map(([kind, name]) => [o.owner, name, ...cells(o[kind])]))}
        empty="No reports or UCs yet."
      />
    </>
  );
}

function documentStatus(document: SourceDocument): string {
  if (document.status === "blocked") return "Extraction blocked";
  if (document.status === "retry_required") return "Retry required";
  if (document.status === "needs_review") return "Extracted";
  if (document.status === "approved") return "Previously approved";
  return document.status[0].toUpperCase() + document.status.slice(1);
}

const CURRENT_DOCUMENT_KEY = "obligot.currentDocument";

function readCurrentDocument(): string | null {
  try {
    return window.localStorage.getItem(CURRENT_DOCUMENT_KEY);
  } catch {
    return null;
  }
}

function rememberCurrentDocument(documentId: string | null) {
  try {
    if (documentId) window.localStorage.setItem(CURRENT_DOCUMENT_KEY, documentId);
    else window.localStorage.removeItem(CURRENT_DOCUMENT_KEY);
  } catch {
    // Storage unavailable (private window): the page still works, it just will not remember.
  }
}

function DocumentsPage({ partners }: { partners: Partner[] }) {
  const [showArchived, setShowArchived] = useState(false);
  const data = useResource(() => api.documents.list({ includeArchived: showArchived }), [showArchived]);
  const [manageId, setManageId] = useState<string | null>(null);
  const [manageMessage, setManageMessage] = useState("");
  // MOUs are contracts kept for audit: records created → archive (restorable); never used → remove the upload.
  const manage = async (document: SourceDocument, action: "archive" | "restore" | "remove") => {
    let reason = "";
    if (action === "archive") {
      reason = window.prompt(`Archive “${document.filename}”? Its agreement, project, reports, UCs and alerts will be hidden (restorable). Reason:`)?.trim() ?? "";
      if (reason.length < 3) return;
    } else if (action === "remove" && !window.confirm(`Permanently remove the upload “${document.filename}”, its pages and extracted values? This cannot be undone.`)) {
      return;
    }
    setManageId(document.id);
    setManageMessage("");
    try {
      if (action === "archive") await api.documents.archive(document.id, reason);
      else if (action === "restore") await api.documents.restore(document.id);
      else await api.documents.remove(document.id);
      if (document.id === currentId && action !== "restore") chooseCurrent(null);
      setManageMessage(action === "archive" ? `Archived “${document.filename}”.` : action === "restore" ? `Restored “${document.filename}”.` : `Removed “${document.filename}”.`);
      data.reload();
    } catch (err) {
      setManageMessage(err instanceof Error ? err.message : "That did not work.");
    } finally {
      setManageId(null);
    }
  };
  const [kind, setKind] = useState<"mou" | "addendum">("mou");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // The current document stays on this page (across navigation and reloads) until "Add new document".
  const [currentId, setCurrentId] = useState<string | null>(() => readCurrentDocument());
  const uploaded = (data.data ?? []).find((d) => d.id === currentId) ?? null;
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [retryError, setRetryError] = useState("");
  const chooseCurrent = (documentId: string | null) => {
    rememberCurrentDocument(documentId);
    setCurrentId(documentId);
  };
  const upload = async (file: File) => {
    setBusy(true);
    setError("");
    try {
      const saved = await api.documents.upload(file, kind);
      chooseCurrent(saved.id);
      data.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  };
  const retry = async (documentId: string) => {
    setRetryingId(documentId);
    setRetryError("");
    try {
      await api.documents.extract(documentId);
      data.reload();
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : "Extraction could not be retried.");
    } finally {
      setRetryingId(null);
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
            <EnumOptions group="document_kind" current={kind} />
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
              event.currentTarget.value = "";
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
            Current document: “{uploaded.filename}” ({uploaded.page_count ?? "?"} pages, {documentStatus(uploaded)})
            {uploaded.agreement_id ? " · records created" : ""}
          </span>
          <Link className="btn small-btn" to={`/documents/${uploaded.id}`}>
            {uploaded.extraction?.finished_at ? "Open results" : "Open to extract"}
          </Link>
          <button className="btn outline small-btn" type="button" onClick={() => chooseCurrent(null)}>
            Add new document
          </button>
        </div>
      )}
      {retryError && (
        <p className="api-state error" role="alert">
          {retryError}
        </p>
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
          <small>Uploaded documents are distinct from the synthetic demo samples.</small>
        </h3>
        <label className="inline-check">
          <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} /> Show archived
        </label>
        {manageMessage && <p className="import-message" role="status">{manageMessage}</p>}
        <DataTable
          headers={[
            "Filename",
            "Type",
            "Partner",
            "Agreement",
            "Uploaded",
            "Status",
            "Action",
          ]}
          rows={(data.data ?? []).map((document) => [
            <Link to={`/documents/${document.id}`} key={document.id}>
              {document.filename}
              {document.source_label === "demo" && <small className="synthetic-row-label">Synthetic sample · no source PDF</small>}
            </Link>,
            document.kind.toUpperCase(),
            partners.find((partner) => partner.id === document.partner_id)
              ?.name ?? "Not linked",
            document.agreement_id ? "Records created" : document.extraction?.finished_at ? "Not yet — open to create records" : "Not linked",
            formatDate(document.uploaded_at),
            <span
              className={`pill ${document.status === "failed" || document.status === "blocked" ? "high" : ""}`}
              key="status"
            >
              {document.archived ? "Archived" : documentStatus(document)}
            </span>,
            <div className="button-row" key="actions">
              <Link className="btn small-btn" to={`/documents/${document.id}`} onClick={() => chooseCurrent(document.id)}>
                Open
              </Link>
              {document.source_label !== "demo" && (document.status === "retry_required" || document.status === "blocked") && (
                <button
                  className="btn outline small-btn"
                  disabled={retryingId !== null}
                  onClick={() => void retry(document.id)}
                >
                  {retryingId === document.id ? "Retrying…" : "Retry extraction"}
                </button>
              )}
              {document.source_label !== "demo" && document.status !== "extracting" && (
                <button
                  className="btn outline small-btn"
                  disabled={manageId !== null}
                  title={document.archived ? "Bring back this MOU and its records" : document.agreement_id
                    ? "Hide this MOU and its records everywhere; kept for audit" : "Delete this upload (no records were created from it)"}
                  onClick={() => void manage(document, document.archived ? "restore" : document.agreement_id ? "archive" : "remove")}
                >
                  {manageId === document.id ? "Working…" : document.archived ? "Restore" : document.agreement_id ? "Archive" : "Remove upload"}
                </button>
              )}
            </div>,
          ])}
          empty="No documents uploaded yet."
        />
      </section>
    </>
  );
}

const EXTRACTION_GROUPS: { key: Exclude<ProposalCollection, "extracted_fields">; label: string }[] = [
  { key: "tables", label: "Tables" },
  { key: "obligations", label: "Obligations and deadlines" },
  { key: "financial_terms", label: "Financial terms" },
  { key: "clauses", label: "Clauses" },
  { key: "programme_scope", label: "Programme scope" },
];

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
          : evidence.basis === "ocr_text"
            ? "found in OCR text of a scanned page — compare with the image"
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

function DocumentReviewPage({ partners }: { partners: Partner[] }) {
  const location = useLocation();
  const documentId = location.pathname.split("/")[2] ?? "";
  const data = useResource<DocumentReview>(() => api.documents.review(documentId), [documentId]);
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(1);
  const [partnerChoice, setPartnerChoice] = useState("");
  const [partnerName, setPartnerName] = useState<string | null>(null);
  const [dealChoice, setDealChoice] = useState("");
  const pipeline = useResource(() => api.opportunities.list(), []);
  useEffect(() => {
    if (documentId) rememberCurrentDocument(documentId);
  }, [documentId]);
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
  if (!review) return <p className="api-state">No extraction data available.</p>;
  const doc = review.document;
  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setMessage(null);
    try {
      await action();
      setMessage({ text: success, error: false });
      data.reload();
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "The request failed.", error: true });
    } finally {
      setBusy(false);
    }
  };
  const extraction = doc.extraction;
  const canExtract = doc.source_label !== "demo"
    && ["uploaded", "failed", "blocked", "needs_review", "extracted", "retry_required"].includes(doc.status);
  const downloadWorkbook = () => void run(async () => {
    const blob = await api.documents.exportDocumentWorkbook(documentId);
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = `obligot-${documentId}-extraction.xlsx`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, "Editable extraction workbook downloaded.");
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
        {doc.source_label === "demo" && (
          <p className="api-state demo-notice" role="note">
            Synthetic demonstration record only. No source PDF was uploaded or processed, and no page evidence is available.
          </p>
        )}
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
        {doc.status !== "extracting" && extraction?.finished_at && (
          <p className={`api-state ${extraction.mode === "groq" || extraction.mode === "gemini" ? "" : "error"}`} role="status">
            {doc.source_label === "demo"
              ? "Synthetic example values only; no document was extracted."
              : extraction.mode === "groq" || extraction.mode === "gemini"
              ? "AI extraction complete."
              : extraction.mode === "partial"
                ? "Partly extracted: AI finished some parts; the rest was pattern-matched only (dates, references, amounts)."
                : "Not extracted by AI: only pattern matching (dates, references, amounts with a currency) was possible."}{" "}
            {extraction.note}
            {extraction.retryable ? " Retry extraction to complete missing pages or parts." : ""}
          </p>
        )}
        {doc.status === "extracting" && extraction && (
          <p className="api-state" role="status">
            {extraction.pages_read < extraction.pages_to_read
              ? `Reading scanned pages: ${extraction.pages_read} of ${extraction.pages_to_read}…`
              : `Extracting values: part ${extraction.chunks_done} of ${extraction.chunks_total || "?"}…`}
          </p>
        )}
        {canExtract && (
          <div className="button-row">
            <button
              className="btn small-btn"
              disabled={busy}
              onClick={() => void run(() => api.documents.extract(documentId), "Extraction started. Progress will update here.")}
            >
              {doc.status === "retry_required" ? "Retry extraction" : extraction?.finished_at ? "Re-run extraction" : "Read & extract"}
            </button>
          </div>
        )}
        {extraction?.finished_at && doc.status !== "extracting" && (
          <button className="btn" disabled={busy} onClick={downloadWorkbook}>
            Download editable Excel workbook
          </button>
        )}
        {message && (
          <p className={`api-state ${message.error ? "error" : "success"}`} role={message.error ? "alert" : "status"}>
            {message.text}
          </p>
        )}
      </section>
      {doc.kind === "mou" && doc.source_label !== "demo" && extraction?.finished_at && doc.status !== "extracting" && (
        <MouPipelineDeal document={doc} partners={partners} />
      )}
      {doc.kind === "mou" && extraction?.finished_at && doc.status !== "extracting" && (
        <MouChecklist review={review} deals={pipeline.data ?? []} partnerId={partnerChoice || doc.partner_id || ""}
          dealId={dealChoice || ""} />
      )}
      {doc.source_label !== "demo" && doc.kind === "mou" && extraction?.finished_at && doc.status !== "extracting" && (
        <section className="box">
          <h3>Use this MOU in ObliGOT</h3>
          {doc.agreement_id ? (
            <p className="api-state success" role="status">
              Records were created from this MOU (agreement {doc.agreement_id}). Its deadlines and fund releases now appear in
              Alerts, Agreements, Projects, Finance, and Reports. <Link to="/alerts">View alerts</Link>
            </p>
          ) : (
            <>
              <p>
                Check the extracted values above first. This creates the partner, agreement, project, reports, utilisation
                certificates, and budget from them, so alerts are calculated from this MOU. Missing dates stay missing.
              </p>
              <div className="toolbar">
                <label>
                  Partner{" "}
                  <select value={partnerChoice} onChange={(event) => setPartnerChoice(event.target.value)}>
                    <option value="">Create a new partner</option>
                    {partners.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
                {!partnerChoice && (
                  <label>
                    Partner name{" "}
                    <input
                      value={partnerName ?? String(review.fields.find((f) => f.field === "partner_name")?.proposed_value ?? "")}
                      onChange={(event) => setPartnerName(event.target.value)}
                      placeholder="As named in the MOU"
                    />
                  </label>
                )}
                <label>
                  Pipeline deal{" "}
                  <select value={dealChoice} onChange={(event) => setDealChoice(event.target.value)}>
                    <option value="">Not in the pipeline</option>
                    {(pipeline.data ?? []).filter((o) => !partnerChoice || o.partner_id === partnerChoice).map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.title} ({o.stage})
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="btn"
                  disabled={busy}
                  onClick={() =>
                    void run(
                      () =>
                        api.documents.createRecords(documentId, {
                          ...(partnerChoice
                            ? { partner_id: partnerChoice }
                            : { partner_name: (partnerName ?? String(review.fields.find((f) => f.field === "partner_name")?.proposed_value ?? "")).trim() || undefined }),
                          opportunity_id: dealChoice || undefined,
                        }),
                      "Records created. Alerts are now calculated from this MOU.",
                    )
                  }
                >
                  Create records from this MOU
                </button>
              </div>
            </>
          )}
        </section>
      )}
      <div className="review-workspace">
        <section className="box">
          <h3>Extracted values</h3>
          <p>Values are exported with their source evidence. They stay with this document until you create records from it.</p>
          {review.fields.length ? (
            review.fields.map((field) => (
              <div className="review-field" key={field.id}>
                <div>
                  <b>{field.field.replaceAll("_", " ")}</b>
                  <small>
                    {String(field.approved_value ?? field.proposed_value ?? "Not stated")} · as written: {field.verbatim || "No verbatim source text recorded."}
                  </small>
                  <EvidenceLine evidence={field.evidence} onShow={setPage} />
                  {field.warnings.map((w) => (
                    <small key={w}>⚠ {w}</small>
                  ))}
                </div>
              </div>
            ))
          ) : (
            <p>No extracted fields are available yet.</p>
          )}
          {EXTRACTION_GROUPS.map(({ key, label }) => {
            const items = review[key] as unknown as (Record<string, unknown> & { id: string; warnings: string[]; evidence?: DocumentEvidence | null })[];
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
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
          {review.issues.length > 0 && <h3>Extraction notes</h3>}
          {review.issues.map((issue) => (
            <div className="review-field" key={issue.id}>
              <div>
                <b>
                  {issue.code.replaceAll("_", " ").toLowerCase()} ({issue.severity})
                </b>
                <small>{issue.message}</small>
              </div>
            </div>
          ))}
        </section>
        <aside className="box evidence-panel">
          <h3>Source page</h3>
          {(doc.page_count ?? 0) > 0 ? (
            <PageViewer documentId={documentId} pageCount={doc.page_count ?? 0} page={Math.min(page, doc.page_count ?? 1)} onPage={setPage} />
          ) : (
            <p>{doc.source_label === "demo" ? "Synthetic example only; no source PDF or pages exist." : "The file could not be read, so there are no pages to show."}</p>
          )}
        </aside>
      </div>
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
  const options = useResource(() => api.options(), []);
  const [entityType, setEntityType] = useState("projects");
  const [file, setFile] = useState<File | null>(null);
  const parse = async (file: File) => {
    setBusy(true);
    setPreview(null);
    setFile(file);
    setMessage("");
    try {
      const result = await api.importPreview(file, entityType);
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
    setExportMessage("Preparing operational workbook…");
    try {
      const blob = await api.documents.exportWorkbook();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "obligot-operational-workbook.xlsx";
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
          <h3>Operational-record export</h3>
          <p>
            This workbook contains operational records. Extracted PDF values are kept separate;
            open a document and download its editable workbook to export its fields and evidence.
          </p>
          <p className="mono">
            Sheets: Partners · Agreements · Programmes_Projects · Programme_Scope ·
            Financial_Terms · Obligations_Milestones · Clauses ·
            Addenda_Change_History · Validation_Review_Issues · About
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
          <div className="toolbar">
            <label>
              Records in the file{" "}
              <select value={entityType} onChange={(event) => setEntityType(event.target.value)}>
                {(options.data?.enums.import_entity_type ?? [entityType]).map((type) => (
                  <option key={type} value={type}>
                    {type.replaceAll("-", " ")}
                  </option>
                ))}
              </select>
            </label>
          </div>
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
              <p className="import-message">{message}</p>
              {file && <ImportCommitPanel key={`${file.name}-${file.lastModified}-${entityType}`} file={file} entityType={entityType} />}
            </>
          )}
        </>
      )}
    </div>
  );
}

/** Cleaned rows → CSV in the browser, with a Problems column; rejected rows are kept so nothing is silently lost. */
function cleanedCsv(result: ImportCommitResult): string {
  const rows = [...result.cleaned, ...result.rejected].sort((a, b) => a.row - b.row);
  const fields = Array.from(new Set(rows.flatMap((r) => Object.keys(r.data))));
  const cell = (value: unknown) => {
    const text = value === null || value === undefined ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  const lines = [["Source row", ...fields, "Result", "Problems"].map(cell).join(",")];
  for (const r of rows) {
    lines.push([r.row, ...fields.map((f) => r.data[f]), r.errors.length ? "Rejected" : "Clean",
      [...r.errors, ...r.warnings].join("; ")].map(cell).join(","));
  }
  return lines.join("\n");
}

function ImportCommitPanel({ file, entityType }: { file: File; entityType: string }) {
  const [result, setResult] = useState<ImportCommitResult | null>(null);
  const [state, setState] = useState<"checking" | "ready" | "saving" | "saved" | "error">("checking");
  const [error, setError] = useState("");
  const run = useCallback(async (dryRun: boolean) => {
    setState(dryRun ? "checking" : "saving");
    setError("");
    try {
      setResult(await api.importCommit(file, entityType, dryRun));
      setState(dryRun ? "ready" : "saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
      setState("error");
    }
  }, [file, entityType]);
  useEffect(() => { void run(true); }, [run]);
  const download = () => {
    if (!result) return;
    const url = URL.createObjectURL(new Blob(["﻿" + cleanedCsv(result)], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `cleaned-${file.name.replace(/\.(csv|xlsx|xlsm)$/i, "")}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  if (state === "checking") return <p className="api-state" role="status">Cleaning the sheet…</p>;
  if (state === "error" || !result) {
    return (
      <p className="api-state error" role="alert">
        {error || "Import failed."} <button className="btn small-btn" onClick={() => void run(true)}>Retry</button>
      </p>
    );
  }
  const problems = result.rejected.slice(0, 8);
  return (
    <section className="box validation">
      <h3>{state === "saved" ? "Import complete" : "Cleaned and ready to import"}</h3>
      <p>
        Header found on row {result.header_row}. Columns matched:{" "}
        {Object.entries(result.mapping).map(([header, field]) => `${header} → ${field}`).join(", ") || "none"}.
        {result.unmapped.length > 0 && ` Ignored: ${result.unmapped.join(", ")}.`}
      </p>
      <div>
        <span className="pill">{state === "saved" ? `Saved · ${result.created}` : `Ready · ${result.valid_count}`}</span>
        <span className="pill high">Rejected · {result.rejected.length}</span>
        <span className="pill">Duplicates skipped · {result.skipped.length}</span>
        {result.new_partners.length > 0 && <span className="pill">New partners · {result.new_partners.length}</span>}
      </div>
      {problems.map((r) => <p key={r.row}>Row {r.row}: {r.errors.join("; ")}</p>)}
      {result.rejected.length > problems.length && <p>…and {result.rejected.length - problems.length} more in the cleaned file.</p>}
      {state === "saved" && <p>Saved records now appear on their pages, and alerts are computed from them automatically.</p>}
      <div className="button-row">
        {state === "ready" && (
          <button className="btn" disabled={result.valid_count === 0 && !result.updated} onClick={() => void run(false)}>
            Import {result.valid_count} valid rows{result.updated ? ` and update ${result.updated} existing partners` : ""}
          </button>
        )}
        {state === "saving" && <button className="btn" disabled>Saving…</button>}
        <button className="btn outline" onClick={download}>Download cleaned sheet</button>
      </div>
    </section>
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
  const keyFacts = [...alert.facts, ...alert.computed].slice(0, 2);
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
      <DrawerSection title="Key details">
        {keyFacts.map((fact) => (
          <div className="evidence" key={fact.label}>
            <span className="mono">{fact.label}</span>
            <b className="mono">{String(fact.value)}</b>
          </div>
        ))}
        <div className="evidence">
          <span>Why it matters</span>
          <b>{alert.why}</b>
        </div>
        <div className="evidence">
          <span>Next step</span>
          <b>{alert.recommendation}</b>
        </div>
        {alert.demo && <small>From a fictional demo record.</small>}
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
        path="/finance"
        element={
          <RequireAuth>
            <Navigate to="/reports" replace />
          </RequireAuth>
        }
      />
      <Route
        path="/partner-360"
        element={
          <RequireAuth>
            <Navigate to="/dashboard" replace />
          </RequireAuth>
        }
      />
      <Route
        path="*"
        element={
          <RequireAuth>
            <OptionsProvider>
              <AppShell />
            </OptionsProvider>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
