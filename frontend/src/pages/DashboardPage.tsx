import {useEffect,useState,type ReactNode} from "react";
import {CalendarClock,CircleAlert,FileClock,Handshake,RefreshCw,Sparkles} from "lucide-react";
import {Link} from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import {api} from "../services/functions.service";
import type {ActionItem,HealthResponse,Partner} from "../types";
import {formatDate,titleCase} from "../lib/utils";
export default function DashboardPage(){
 const [partners,setPartners]=useState<Partner[]>([]);const [actions,setActions]=useState<ActionItem[]>([]);
 const [health,setHealth]=useState<HealthResponse|null>(null);const [error,setError]=useState("");const [loading,setLoading]=useState(true);
 async function load(){setLoading(true);setError("");try{const [p,a,h]=await Promise.all([api.partners(),api.actions(),api.health()]);setPartners(p);setActions(a);setHealth(h);}catch(e){setError(e instanceof Error?e.message:"Could not load API data.");}finally{setLoading(false);}}
 useEffect(()=>{void load();},[]);
 const active=partners.filter(p=>p.status==="active").length;const open=actions.filter(a=>a.status!=="done").length;const high=actions.filter(a=>a.priority==="high"&&a.status!=="done").length;
 return <>
  <PageHeader eyebrow="MANAGEMENT OVERVIEW" title="Partnership overview" description="A consolidated view of relationships, commitments, and the next actions that need attention." action={<button className="button button-secondary" onClick={()=>void load()}><RefreshCw size={15}/> Refresh</button>}/>
  {error&&<StateMessage kind="error" title="API connection unavailable" detail={`${error} Start the FastAPI backend and retry.`}/>}
  <div className="notice"><Sparkles size={17}/><div><strong>Evidence first. AI second.</strong><p>Deadline findings come from rules. AI interpretations should be reviewed before action.</p></div><span className="notice-tag">{health?.ai_configured?"AI CONFIGURED":"RULES-FIRST MODE"}</span></div>
  <div className="metric-grid"><Metric icon={<Handshake size={19}/>} label="Partners tracked" value={loading?"—":String(partners.length)} note="Records currently available"/><Metric icon={<CalendarClock size={19}/>} label="Active partnerships" value={loading?"—":String(active)} note="Based on stored status"/><Metric icon={<CircleAlert size={19}/>} label="Open actions" value={loading?"—":String(open)} note="Not marked complete"/><Metric icon={<FileClock size={19}/>} label="High-priority actions" value={loading?"—":String(high)} note="Review recommended"/></div>
  <div className="content-grid">
   <section className="panel"><div className="panel-heading"><div><h2>Priority action queue</h2><p>Review the evidence and decide what happens next.</p></div><Link to="/actions" className="text-link">View all →</Link></div>
    {loading?<StateMessage kind="loading" title="Loading actions…"/>:actions.length?<div className="action-list">{actions.slice(0,5).map(item=><div className="action-row" key={item.id}><span className={`priority-dot ${item.priority}`}/><div className="action-copy"><strong>{item.title}</strong><span>{item.evidence[0]||"No supporting evidence supplied"}</span></div><div className="action-meta"><span className={`status-pill ${item.priority}`}>{titleCase(item.priority)}</span><small>{formatDate(item.due_date)}</small></div></div>)}</div>:<StateMessage title="No actions returned" detail="Connect records and rules to populate this queue."/>}
   </section>
   <section className="panel"><div className="panel-heading"><div><h2>Partner directory</h2><p>Illustrative records from the API.</p></div><Link to="/partners" className="text-link">Open directory →</Link></div>
    {loading?<StateMessage kind="loading" title="Loading partners…"/>:partners.slice(0,5).map(p=><Link to={`/partners/${p.id}`} className="partner-row" key={p.id}><div className="partner-avatar">{p.name.slice(0,1).toUpperCase()}</div><div className="partner-copy"><strong>{p.name}</strong><span>{p.category} · {p.owner}</span></div><span className={`status-pill ${p.status}`}>{titleCase(p.status)}</span></Link>)}
    {!loading&&!partners.length&&<StateMessage title="No partner records" detail="The backend currently has no partner records."/>}
   </section>
  </div>
  <div className="bottom-grid"><div className="info-card"><div className="info-icon"><CircleAlert size={19}/></div><div><strong>Keep risk explainable</strong><p>Every flag should show the record, triggering rule, and recommended owner action.</p></div></div><div className="info-card"><div className="info-icon"><Sparkles size={19}/></div><div><strong>Human review stays in control</strong><p>Recommendations are drafts until a team member reviews and records a decision.</p></div></div></div>
 </>;
}
function Metric({icon,label,value,note}:{icon:ReactNode;label:string;value:string;note:string}){return <div className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>;}
