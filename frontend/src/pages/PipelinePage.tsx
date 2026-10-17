import {useState} from "react";
import {Plus} from "lucide-react";
import Dialog from "../components/ui/Dialog";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import OpportunityForm from "../features/pipeline/OpportunityForm";
import OpportunityTable from "../features/pipeline/OpportunityTable";
import {api} from "../services/functions.service";
import {useResource} from "../lib/useResource";
import {STAGES,nextStage,stageLabel} from "../lib/pipeline";
import type {Opportunity,OpportunityStage} from "../types";

export default function PipelinePage(){
 const {data,error,loading,reload}=useResource(async()=>{
  const [opportunities,partners]=await Promise.all([api.opportunities.list(),api.partners.list()]);
  return {opportunities,partners};
 },[]);
 const [stage,setStage]=useState<OpportunityStage|"all">("all");
 const [dialog,setDialog]=useState<{mode:"create"}|{mode:"edit";opportunity:Opportunity}|null>(null);
 const [busyId,setBusyId]=useState<string|null>(null);
 const [actionError,setActionError]=useState("");
 const [notice,setNotice]=useState("");
 const opportunities=data?.opportunities??[];
 const partnerName=new Map((data?.partners??[]).map(p=>[p.id,p.name]));
 const counts=Object.fromEntries(STAGES.map(s=>[s.id,opportunities.filter(o=>o.stage===s.id).length])) as Record<OpportunityStage,number>;
 const stageOrder=(o:Opportunity)=>STAGES.findIndex(s=>s.id===o.stage);
 const shown=opportunities.filter(o=>stage==="all"||o.stage===stage)
  .sort((a,b)=>stageOrder(a)-stageOrder(b)||(a.next_step_date??"9999").localeCompare(b.next_step_date??"9999"));

 async function advance(o:Opportunity){
  const next=nextStage(o.stage); if(!next)return;
  setBusyId(o.id);setActionError("");setNotice("");
  try{await api.opportunities.update(o.id,{stage:next});setNotice(`Moved “${o.title}” to ${stageLabel(next)}.`);reload();}
  catch(e){setActionError(e instanceof Error?e.message:"Could not update the stage.");}
  finally{setBusyId(null);}
 }
 const finish=(message:string)=>{setDialog(null);setNotice(message);reload();};

 return <>
  <PageHeader eyebrow="PARTNERSHIP OPERATIONS" title="Partnership pipeline" description="Track prospective and existing partnerships through each lifecycle stage. Stages are recorded by the team; they never imply a signed agreement." action={<button className="button button-primary" onClick={()=>setDialog({mode:"create"})} disabled={!data}><Plus size={15} aria-hidden/> Add opportunity</button>}/>
  {error&&<StateMessage kind="error" title="Could not load the pipeline" detail={error.message} action={<button className="button button-secondary" onClick={reload}>Retry</button>}/>}
  {actionError&&<p className="form-error page-message" role="alert">{actionError}</p>}
  {notice&&<p className="success-message page-message" role="status">{notice}</p>}
  {loading&&!data?<StateMessage kind="loading" title="Loading pipeline…"/>:data&&<>
   <div className="stage-strip" role="group" aria-label="Filter by stage">
    <button className={`stage-chip${stage==="all"?" active":""}`} aria-pressed={stage==="all"} onClick={()=>setStage("all")}><span>All stages</span><strong>{opportunities.length}</strong></button>
    {STAGES.map(s=><button key={s.id} className={`stage-chip${stage===s.id?" active":""}`} aria-pressed={stage===s.id} onClick={()=>setStage(s.id)}><span>{s.label}</span><strong>{counts[s.id]}</strong></button>)}
   </div>
   <div className="panel table-panel">
    {shown.length?<OpportunityTable rows={shown} partnerName={id=>partnerName.get(id)} onAdvance={o=>void advance(o)} onEdit={o=>setDialog({mode:"edit",opportunity:o})} busyId={busyId}/>
     :<StateMessage title={opportunities.length?`No opportunities at ${stage==="all"?"any stage":stageLabel(stage)}`:"No opportunities yet"} detail={opportunities.length?"Choose another stage or add an opportunity.":"Use “Add opportunity” to record the first one."}/>}
   </div>
  </>}
  <Dialog open={dialog!==null} title={dialog?.mode==="edit"?"Edit opportunity":"Add opportunity"} onClose={()=>setDialog(null)}>
   {dialog&&<OpportunityForm opportunity={dialog.mode==="edit"?dialog.opportunity:undefined} partners={data?.partners??[]}
     onCancel={()=>setDialog(null)} onSaved={saved=>finish(dialog.mode==="edit"?`Saved “${saved.title}”.`:`Added “${saved.title}”.`)}
     onDeleted={dialog.mode==="edit"?()=>finish(`Deleted “${dialog.opportunity.title}”.`):undefined}/>}
  </Dialog>
 </>;
}
