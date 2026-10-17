import {useRef,useState,type KeyboardEvent,type ReactNode} from "react";
import {Pencil,Trash2} from "lucide-react";
import {Link,useNavigate,useParams} from "react-router-dom";
import Dialog from "../components/ui/Dialog";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import StatusBadge from "../components/ui/StatusBadge";
import FindingList from "../features/intelligence/FindingList";
import PartnerForm from "../features/partners/PartnerForm";
import {ActionTable,AgreementTable,FinanceTable,ProjectTable,ReportTable} from "../features/partners/LinkedRecordTables";
import {ApiError,api} from "../services/functions.service";
import {useResource} from "../lib/useResource";
import {formatDate} from "../lib/utils";
import type {DeadlineFinding,Partner} from "../types";

type TabId="overview"|"agreements"|"projects"|"finance"|"reports"|"actions";

export default function PartnerDetailsPage(){
 const {partnerId=""}=useParams();
 const partner=useResource(()=>api.partners.get(partnerId),[partnerId]);
 const linked=useResource(async()=>{
  const [agreements,projects,finance,reports,actions,dashboard]=await Promise.all([
   api.agreements.list(partnerId),api.projects.list(partnerId),api.finance.list(partnerId),
   api.reports.list(partnerId),api.actions.list({relatedPartnerId:partnerId}),api.dashboard(),
  ]);
  const rank={high:0,medium:1,low:2};
  const findings=dashboard.findings.filter(f=>f.partner_id===partnerId)
   .sort((a,b)=>rank[a.priority]-rank[b.priority]||(a.days_remaining??Infinity)-(b.days_remaining??Infinity));
  return {agreements,projects,finance,reports,actions,findings,asOf:dashboard.as_of};
 },[partnerId]);
 const [tab,setTab]=useState<TabId>("overview");
 const [editing,setEditing]=useState(false);
 const [deleting,setDeleting]=useState(false);
 const notFound=partner.error instanceof ApiError&&partner.error.status===404;
 const p=partner.data;

 return <><PageHeader eyebrow="PARTNER 360" title={p?.name||"Partner profile"} description="A single view of the relationship and its linked obligations." action={<div className="header-actions">{p&&<><button className="button button-secondary" onClick={()=>setEditing(true)}><Pencil size={14} aria-hidden/> Edit</button><button className="button button-danger" onClick={()=>setDeleting(true)}><Trash2 size={14} aria-hidden/> Delete</button></>}<Link to="/partners" className="button button-secondary">Back to partners</Link></div>}/>
 {partner.loading&&<StateMessage kind="loading" title="Loading partner record…"/>}
 {!partner.loading&&notFound&&<StateMessage title="Partner not found" detail={`No partner exists with ID “${partnerId}”. It may have been deleted.`}/>}
 {!partner.loading&&partner.error&&!notFound&&<StateMessage kind="error" title="Could not load partner" detail={partner.error.message} action={<button className="button button-secondary" onClick={partner.reload}>Retry</button>}/>}
 {!partner.loading&&p&&<>
  <ProfilePanel partner={p}/>
  {linked.error&&<StateMessage kind="error" title="Could not load linked records" detail={linked.error.message} action={<button className="button button-secondary" onClick={linked.reload}>Retry</button>}/>}
  {linked.loading&&<StateMessage kind="loading" title="Loading agreements, projects, finance, reports, and actions…"/>}
  {linked.data&&<Tabs tab={tab} onChange={setTab} counts={{overview:linked.data.findings.length,agreements:linked.data.agreements.length,projects:linked.data.projects.length,finance:linked.data.finance.length,reports:linked.data.reports.length,actions:linked.data.actions.length}}>
   {tab==="overview"&&<OverviewTab findings={linked.data.findings} asOf={linked.data.asOf}/>}
   {tab==="agreements"&&<AgreementTable rows={linked.data.agreements}/>}
   {tab==="projects"&&<ProjectTable rows={linked.data.projects}/>}
   {tab==="finance"&&<FinanceTable rows={linked.data.finance}/>}
   {tab==="reports"&&<ReportTable rows={linked.data.reports}/>}
   {tab==="actions"&&<ActionTable rows={linked.data.actions}/>}
  </Tabs>}
  <Dialog open={editing} title="Edit partner" onClose={()=>setEditing(false)}>
   <PartnerForm partner={p} onCancel={()=>setEditing(false)} onSaved={()=>{setEditing(false);partner.reload();}}/>
  </Dialog>
  <DeletePartnerDialog open={deleting} partner={p} onClose={()=>setDeleting(false)}/>
 </>}
 </>;
}

function ProfilePanel({partner}:{partner:Partner}){
 return <div className="panel detail-panel"><div className="detail-heading"><div className="partner-avatar large" aria-hidden>{partner.name.slice(0,1)}</div><div><h2>{partner.name}</h2><p>{partner.category} · Owner: {partner.owner}</p></div><StatusBadge value={partner.status}/></div>
  <p>{partner.summary||"No summary recorded."}</p>
  <dl className="detail-grid detail-grid-four">
   <div><dt>Contact</dt><dd>{partner.contact_name||"Not recorded"}</dd></div>
   <div><dt>Contact email</dt><dd>{partner.contact_email?<a className="text-link" href={`mailto:${partner.contact_email}`}>{partner.contact_email}</a>:"Not recorded"}</dd></div>
   <div><dt>Last updated</dt><dd>{formatDate(partner.updated_at)}</dd></div>
   <div><dt>Record source</dt><dd>{partner.source_label==="demo"?"Demo (fictional)":"User entered"}</dd></div>
  </dl>
 </div>;
}

const TABS:{id:TabId;label:string}[]=[{id:"overview",label:"Open findings"},{id:"agreements",label:"Agreements"},{id:"projects",label:"Projects"},{id:"finance",label:"Finance"},{id:"reports",label:"Reports"},{id:"actions",label:"Actions"}];

function Tabs({tab,onChange,counts,children}:{tab:TabId;onChange:(t:TabId)=>void;counts:Record<TabId,number>;children:ReactNode}){
 const refs=useRef<Record<string,HTMLButtonElement|null>>({});
 function onKey(e:KeyboardEvent){
  const i=TABS.findIndex(t=>t.id===tab);
  const next=e.key==="ArrowRight"?(i+1)%TABS.length:e.key==="ArrowLeft"?(i-1+TABS.length)%TABS.length:e.key==="Home"?0:e.key==="End"?TABS.length-1:-1;
  if(next<0)return;
  e.preventDefault();onChange(TABS[next].id);refs.current[TABS[next].id]?.focus();
 }
 return <section className="panel tab-panel">
  <div className="tab-list" role="tablist" aria-label="Partner records" onKeyDown={onKey}>
   {TABS.map(t=><button key={t.id} ref={el=>{refs.current[t.id]=el;}} role="tab" id={`tab-${t.id}`} aria-selected={tab===t.id} aria-controls={`panel-${t.id}`} tabIndex={tab===t.id?0:-1} className={`tab${tab===t.id?" active":""}`} onClick={()=>onChange(t.id)}>{t.label}<span className="tab-count">{counts[t.id]}</span></button>)}
  </div>
  <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="tab-body">{children}</div>
 </section>;
}

function OverviewTab({findings,asOf}:{findings:DeadlineFinding[];asOf:string}){
 return <><p className="muted tab-intro">Rule-generated from this partner's agreements, reports, invoices, and UCs as of {formatDate(asOf)} (IST). Resolved records are excluded.</p>
  {findings.length?<FindingList findings={findings}/>:<StateMessage title="No open findings" detail="Nothing linked to this partner is overdue, due within 30 days, or missing a required date."/>}</>;
}

function DeletePartnerDialog({open,partner,onClose}:{open:boolean;partner:Partner;onClose:()=>void}){
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 const navigate=useNavigate();
 async function confirm(){
  setBusy(true);setError("");
  try{await api.partners.remove(partner.id);navigate("/partners");}
  catch(e){setError(e instanceof Error?e.message:"Could not delete the partner.");}
  finally{setBusy(false);}
 }
 const close=()=>{setError("");onClose();};
 return <Dialog open={open} title="Delete partner?" onClose={close}>
  <p className="dialog-text">This permanently deletes <strong>{partner.name}</strong>. Partners with linked agreements, projects, finance records, reports, actions, or follow-ups cannot be deleted.</p>
  {error&&<p className="form-error" role="alert">{error}</p>}
  <div className="form-actions"><button className="button button-secondary" onClick={close} disabled={busy}>Cancel</button><button className="button button-danger" onClick={()=>void confirm()} disabled={busy||Boolean(error)}>{busy?"Deleting…":"Delete partner"}</button></div>
 </Dialog>;
}
