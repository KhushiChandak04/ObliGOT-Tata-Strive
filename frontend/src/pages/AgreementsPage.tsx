import {useState} from "react";
import {Plus} from "lucide-react";
import Dialog from "../components/ui/Dialog";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import AgreementForm from "../features/agreements/AgreementForm";
import {AgreementTable} from "../features/partners/LinkedRecordTables";
import {api} from "../services/functions.service";
import {useResource} from "../lib/useResource";
import {AGREEMENT_STATUSES,SIGNED_COPY} from "../lib/agreements";
import type {Agreement,AgreementStatus,SignedCopyStatus} from "../types";

const EXPIRY_WINDOW_DAYS=60;

export default function AgreementsPage(){
 const [expiringOnly,setExpiringOnly]=useState(false);
 const {data,error,loading,reload}=useResource(async()=>{
  // The expiry window is evaluated by the backend against the IST business date.
  const [agreements,partners,projects,opportunities]=await Promise.all([
   api.agreements.list(undefined,expiringOnly?{expiring_within_days:String(EXPIRY_WINDOW_DAYS)}:{}),
   api.partners.list(),api.projects.list(),api.opportunities.list(),
  ]);
  return {agreements,partners,projects,opportunities};
 },[expiringOnly]);
 const [query,setQuery]=useState("");
 const [status,setStatus]=useState<AgreementStatus|"all">("all");
 const [signed,setSigned]=useState<SignedCopyStatus|"all">("all");
 const [dialog,setDialog]=useState<{mode:"create"}|{mode:"edit";agreement:Agreement}|null>(null);
 const [notice,setNotice]=useState("");
 const partnerName=new Map((data?.partners??[]).map(p=>[p.id,p.name]));
 const all=data?.agreements??[];
 const needle=query.trim().toLowerCase();
 const shown=all.filter(a=>(status==="all"||a.status===status)&&(signed==="all"||a.signed_copy===signed)
  &&(!needle||`${a.title} ${a.reference_number??""} ${partnerName.get(a.partner_id)??""} ${a.owner}`.toLowerCase().includes(needle)))
  .sort((a,b)=>(a.expiry_date??"9999").localeCompare(b.expiry_date??"9999")||a.title.localeCompare(b.title));
 const filtersActive=Boolean(needle)||status!=="all"||signed!=="all"||expiringOnly;
 const clear=()=>{setQuery("");setStatus("all");setSigned("all");setExpiringOnly(false);};
 const finish=(message:string)=>{setDialog(null);setNotice(message);reload();};

 return <>
  <PageHeader eyebrow="PARTNERSHIP OPERATIONS" title="Agreements & MOUs" description="Register of agreements with status, dates, signed-copy and renewal tracking. Status is recorded by the team; a proposal is never treated as a signed agreement." action={<button className="button button-primary" onClick={()=>setDialog({mode:"create"})} disabled={!data}><Plus size={15} aria-hidden/> Add agreement</button>}/>
  <div className="toolbar">
   <input className="search-input" type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search title, reference, partner, or owner…" aria-label="Search agreements"/>
   <label className="toolbar-select"><span>Status</span><select value={status} onChange={e=>setStatus(e.target.value as AgreementStatus|"all")}><option value="all">All</option>{AGREEMENT_STATUSES.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
   <label className="toolbar-select"><span>Signed copy</span><select value={signed} onChange={e=>setSigned(e.target.value as SignedCopyStatus|"all")}><option value="all">All</option>{SIGNED_COPY.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
   <label className="toolbar-check"><input type="checkbox" checked={expiringOnly} onChange={e=>setExpiringOnly(e.target.checked)}/> Active, expiring within {EXPIRY_WINDOW_DAYS} days</label>
   <span className="muted" aria-live="polite">{data?`${shown.length} of ${all.length} agreements`:""}</span>
   {filtersActive&&<button className="text-button" onClick={clear}>Clear filters</button>}
  </div>
  {error&&<StateMessage kind="error" title="Could not load agreements" detail={error.message} action={<button className="button button-secondary" onClick={reload}>Retry</button>}/>}
  {notice&&<p className="success-message page-message" role="status">{notice}</p>}
  {loading&&!data?<StateMessage kind="loading" title="Loading agreements…"/>:data&&<div className="panel">
   <AgreementTable rows={shown} partnerName={id=>partnerName.get(id)} onEdit={a=>setDialog({mode:"edit",agreement:a})}
    emptyTitle={all.length?"No matching agreements":expiringOnly?`No active agreements expire within ${EXPIRY_WINDOW_DAYS} days`:"No agreements yet"}
    emptyDetail={all.length?"Try a different search or filter.":expiringOnly?"Clear the expiry filter to see all agreements.":"Use “Add agreement” to record the first one."}/>
  </div>}
  <Dialog open={dialog!==null} title={dialog?.mode==="edit"?"Edit agreement":"Add agreement"} onClose={()=>setDialog(null)}>
   {dialog&&data&&<AgreementForm agreement={dialog.mode==="edit"?dialog.agreement:undefined} partners={data.partners} projects={data.projects} opportunities={data.opportunities}
     onCancel={()=>setDialog(null)} onSaved={saved=>finish(dialog.mode==="edit"?`Saved “${saved.title}”.`:`Added “${saved.title}”.`)}
     onDeleted={dialog.mode==="edit"?()=>finish(`Deleted “${dialog.agreement.title}”.`):undefined}/>}
  </Dialog>
 </>;
}
