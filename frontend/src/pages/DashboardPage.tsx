import {type ReactNode} from "react";
import {CalendarClock,CircleAlert,Database,FileCheck2,FileClock,FolderKanban,Handshake,ListTodo,RefreshCw,Sparkles} from "lucide-react";
import {Link,useNavigate} from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import StatusBadge from "../components/ui/StatusBadge";
import AlertList from "../features/alerts/AlertList";
import {api} from "../services/functions.service";
import {useResource} from "../lib/useResource";
import {TODAY_COUNT,todaysAlerts} from "../lib/alerts";
import type {ActionItem,Priority} from "../types";
import {formatDate} from "../lib/utils";

const PRIORITY_RANK:Record<Priority,number>={high:0,medium:1,low:2};
const OPEN_ACTION_STATUSES=new Set(["open","in_review"]);

export default function DashboardPage(){
 const navigate=useNavigate();
 const {data,error,loading,reload}=useResource(async()=>{
  const [dashboard,alerts,actions,partners,health]=await Promise.all([api.dashboard(),api.alerts.list(),api.actions.list(),api.partners.list(),api.health()]);
  return {dashboard,alerts,actions,partners,health};
 },[]);
 const m=data?.dashboard.metrics;
 const today=todaysAlerts(data?.alerts.alerts??[]);
 const openActions=(data?.actions??[]).filter(a=>OPEN_ACTION_STATUSES.has(a.status))
  .sort((a:ActionItem,b:ActionItem)=>PRIORITY_RANK[a.priority]-PRIORITY_RANK[b.priority]||(a.due_date??"9999").localeCompare(b.due_date??"9999"));
 const partnerName=new Map((data?.partners??[]).map(p=>[p.id,p.name]));
 const value=(n?:number)=>loading||n===undefined?"—":String(n);
 const counts=data?.alerts.counts;
 return <>
  <PageHeader eyebrow="MANAGEMENT OVERVIEW" title="Partnership overview" description={data?`Consolidated view of relationships, commitments, and next actions. Rules evaluated as of ${formatDate(data.alerts.as_of)} (IST).`:"A consolidated view of relationships, commitments, and the next actions that need attention."} action={<button className="button button-secondary" onClick={reload} disabled={loading}><RefreshCw size={15} aria-hidden/> Refresh</button>}/>
  {error&&<StateMessage kind="error" title="API connection unavailable" detail={`${error.message} Start the FastAPI backend and retry.`} action={<button className="button button-secondary" onClick={reload}>Retry</button>}/>}
  {data?.dashboard.storage_mode==="demo-memory-fallback"&&<div className="notice notice-warning"><Database size={17} aria-hidden/><div><strong>In-memory demo data.</strong><p>Firestore is not configured on the backend, so records are illustrative and are lost when the backend restarts.</p></div><span className="notice-tag">NOT PERSISTENT</span></div>}
  <div className="notice"><Sparkles size={17} aria-hidden/><div><strong>Evidence first. AI second.</strong><p>Alerts come from deterministic rules over stored records. AI interpretations must be reviewed before action.</p></div><span className="notice-tag">{!data?"AI STATUS UNKNOWN":data.health.ai_configured?"AI CONFIGURED":"RULES-FIRST MODE"}</span></div>
  <div className="metric-grid metric-grid-three">
   <Metric icon={<Handshake size={19}/>} label="Partners tracked" value={value(m?.partners_total)} note={m?`${m.partners_active} active`:"Stored partner records"}/>
   <Metric icon={<FileCheck2 size={19}/>} label="Active agreements" value={value(m?.agreements_active)} note="Agreements with status Active"/>
   <Metric icon={<FolderKanban size={19}/>} label="Active projects" value={value(m?.projects_active)} note="Projects with status Active"/>
   <Metric icon={<FileClock size={19}/>} label="Reports pending" value={value(m?.reports_pending)} note="Not submitted or accepted"/>
   <Metric icon={<CalendarClock size={19}/>} label="Open alerts" value={value(counts?.total)} note={counts?`${counts.by_level.high} high · ${counts.by_level.medium} medium · ${counts.by_level.low} low`:"—"} to="/actions"/>
   <Metric icon={<ListTodo size={19}/>} label="Open actions" value={value(m?.actions_open)} note="Not done or deferred" to="/actions"/>
  </div>
  <div className="content-grid">
   <section className="panel" aria-labelledby="today-heading"><div className="panel-heading"><div><h2 id="today-heading">Today's {TODAY_COUNT}</h2><p>Highest-priority open alerts without a task. Open one to see its evidence and act.</p></div><Link to="/actions" className="text-link">All alerts →</Link></div>
    {loading?<StateMessage kind="loading" title="Evaluating rules…"/>:today.length?<AlertList alerts={today} partnerName={id=>partnerName.get(id)} onOpen={a=>navigate(`/actions?alert=${encodeURIComponent(a.id)}`)} ranked/>:!error&&<StateMessage title="Nothing needs attention right now" detail="Every open alert already has a task, or no record triggers a rule."/>}
   </section>
   <section className="panel" aria-labelledby="actions-heading"><div className="panel-heading"><div><h2 id="actions-heading">Open tasks</h2><p>Highest priority first, then earliest due date.</p></div><Link to="/actions" className="text-link">View all →</Link></div>
    {loading?<StateMessage kind="loading" title="Loading tasks…"/>:openActions.length?<div className="action-list">{openActions.slice(0,5).map(item=><Link to={`/actions?task=${encodeURIComponent(item.id)}`} className="action-row" key={item.id}><span className={`priority-dot ${item.priority}`} aria-hidden/><div className="action-copy"><strong>{item.title}</strong><span>{[item.owner,item.evidence[0]||"No supporting evidence supplied"].filter(Boolean).join(" · ")}</span></div><div className="action-meta"><StatusBadge value={item.priority} label={`${item.priority[0].toUpperCase()}${item.priority.slice(1)} priority`}/><small>{formatDate(item.due_date)}</small></div></Link>)}</div>:!error&&<StateMessage title="No open tasks" detail="Tasks that are open or in review will appear here."/>}
   </section>
  </div>
  <div className="bottom-grid">
   <section className="panel" aria-labelledby="partners-heading"><div className="panel-heading"><div><h2 id="partners-heading">Partner directory</h2><p>Most recent records from the API.</p></div><Link to="/partners" className="text-link">Open directory →</Link></div>
    {loading?<StateMessage kind="loading" title="Loading partners…"/>:(data?.partners??[]).slice(0,5).map(p=><Link to={`/partners/${p.id}`} className="partner-row" key={p.id}><div className="partner-avatar" aria-hidden>{p.name.slice(0,1).toUpperCase()}</div><div className="partner-copy"><strong>{p.name}</strong><span>{p.category} · {p.owner}{p.source_label==="demo"?" · demo":""}</span></div><StatusBadge value={p.status}/></Link>)}
    {!loading&&!error&&!data?.partners.length&&<StateMessage title="No partner records" detail="The backend currently has no partner records."/>}
   </section>
   <div className="info-stack"><div className="info-card"><div className="info-icon"><CircleAlert size={19} aria-hidden/></div><div><strong>Keep risk explainable</strong><p>Every alert shows the record, the triggering rule, and the evidence it is based on.</p></div></div><div className="info-card"><div className="info-icon"><Sparkles size={19} aria-hidden/></div><div><strong>Human review stays in control</strong><p>Alerts are acknowledged, deferred, dismissed, or turned into tasks by a person, and every decision is logged.</p></div></div></div>
  </div>
 </>;
}
function Metric({icon,label,value,note,to}:{icon:ReactNode;label:string;value:string;note:string;to?:string}){
 const body=<><div className="metric-top"><span>{label}</span><span className="metric-icon" aria-hidden>{icon}</span></div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></>;
 return to?<Link to={to} className="metric-card metric-link">{body}</Link>:<div className="metric-card">{body}</div>;
}
