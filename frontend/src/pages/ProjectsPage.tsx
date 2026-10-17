import {Fragment,useState} from "react";
import {ChevronDown,ChevronRight,Plus} from "lucide-react";
import {Link} from "react-router-dom";
import Dialog from "../components/ui/Dialog";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import StatusBadge from "../components/ui/StatusBadge";
import MilestoneForm from "../features/projects/MilestoneForm";
import ProjectForm from "../features/projects/ProjectForm";
import {api} from "../services/functions.service";
import {useResource} from "../lib/useResource";
import {MILESTONE_STATUSES,PROJECT_STATUSES} from "../lib/projects";
import {formatDate} from "../lib/utils";
import type {Milestone,Project,RecordStatus} from "../types";

type DialogState=
 |{kind:"project";project?:Project}
 |{kind:"milestone";projectId:string;milestone?:Milestone;markComplete?:boolean};

const milestoneLabel=(status:Milestone["status"])=>MILESTONE_STATUSES.find(s=>s.id===status)?.label??status;

export default function ProjectsPage(){
 const {data,error,loading,reload}=useResource(async()=>{
  const [projects,partners,milestones]=await Promise.all([api.projects.list(),api.partners.list(),api.milestones.list()]);
  return {projects,partners,milestones};
 },[]);
 const [query,setQuery]=useState("");
 const [status,setStatus]=useState<RecordStatus|"all">("all");
 const [expanded,setExpanded]=useState<Set<string>>(new Set());
 const [dialog,setDialog]=useState<DialogState|null>(null);
 const [notice,setNotice]=useState("");
 const partnerName=new Map((data?.partners??[]).map(p=>[p.id,p.name]));
 const milestonesFor=(projectId:string)=>(data?.milestones??[]).filter(m=>m.project_id===projectId)
  .sort((a,b)=>(a.due_date??"9999").localeCompare(b.due_date??"9999"));
 const needle=query.trim().toLowerCase();
 const all=data?.projects??[];
 const shown=all.filter(p=>(status==="all"||p.status===status)&&(!needle||`${p.name} ${p.owner} ${p.partner_id?partnerName.get(p.partner_id)??"":""}`.toLowerCase().includes(needle)))
  .sort((a,b)=>a.name.localeCompare(b.name));
 const toggle=(id:string)=>setExpanded(current=>{const next=new Set(current);if(next.has(id))next.delete(id);else next.add(id);return next;});
 const finish=(message:string)=>{setDialog(null);setNotice(message);reload();};
 const dialogTitle=!dialog?"":dialog.kind==="project"?(dialog.project?"Edit project":"Add project"):dialog.markComplete?"Mark milestone complete":dialog.milestone?"Edit milestone":"Add milestone";

 return <>
  <PageHeader eyebrow="PARTNERSHIP OPERATIONS" title="Projects & milestones" description="Project status and dated delivery milestones. Completion dates are entered by the team, never assumed." action={<button className="button button-primary" onClick={()=>setDialog({kind:"project"})} disabled={!data}><Plus size={15} aria-hidden/> Add project</button>}/>
  <div className="toolbar">
   <input className="search-input" type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search project, partner, or owner…" aria-label="Search projects"/>
   <label className="toolbar-select"><span>Status</span><select value={status} onChange={e=>setStatus(e.target.value as RecordStatus|"all")}><option value="all">All</option>{PROJECT_STATUSES.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
   <span className="muted" aria-live="polite">{data?`${shown.length} of ${all.length} projects`:""}</span>
   {(needle||status!=="all")&&<button className="text-button" onClick={()=>{setQuery("");setStatus("all");}}>Clear filters</button>}
  </div>
  {error&&<StateMessage kind="error" title="Could not load projects" detail={error.message} action={<button className="button button-secondary" onClick={reload}>Retry</button>}/>}
  {notice&&<p className="success-message page-message" role="status">{notice}</p>}
  {loading&&!data?<StateMessage kind="loading" title="Loading projects…"/>:data&&<div className="panel table-panel">
   {shown.length?<table>
    <thead><tr><th scope="col">Project</th><th scope="col">Status</th><th scope="col">Start</th><th scope="col">End</th><th scope="col">Owner</th><th scope="col">Milestones</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead>
    <tbody>{shown.map(p=>{
     const milestones=milestonesFor(p.id);
     const done=milestones.filter(m=>m.status==="completed").length;
     const open=expanded.has(p.id);
     return <Fragment key={p.id}>
      <tr className={open?"row-expanded":undefined}>
       <td><strong>{p.name}</strong><small>{p.partner_id?<Link className="text-link" to={`/partners/${p.partner_id}`}>{partnerName.get(p.partner_id)??p.partner_id}</Link>:"No partner"}{p.source_label==="demo"?" · demo":""}</small></td>
       <td><StatusBadge value={p.status}/></td><td>{formatDate(p.start_date)}</td><td>{formatDate(p.end_date)}</td><td>{p.owner}</td>
       <td><button className="text-button expand-button" onClick={()=>toggle(p.id)} aria-expanded={open} aria-controls={`milestones-${p.id}`}>{open?<ChevronDown size={14} aria-hidden/>:<ChevronRight size={14} aria-hidden/>}{milestones.length?`${done} of ${milestones.length} completed`:"None yet"}</button></td>
       <td className="row-actions"><button className="text-button" onClick={()=>setDialog({kind:"project",project:p})} aria-label={`Edit ${p.name}`}>Edit</button></td>
      </tr>
      {open&&<tr className="expansion-row" id={`milestones-${p.id}`}><td colSpan={7}>
       <div className="milestone-panel">
        <div className="milestone-header"><strong>Milestones for {p.name}</strong><button className="button button-secondary button-small" onClick={()=>setDialog({kind:"milestone",projectId:p.id})}><Plus size={13} aria-hidden/> Add milestone</button></div>
        {milestones.length?<ul className="milestone-list">{milestones.map(m=><li key={m.id}>
         <div><strong>{m.title}</strong><small>Due {formatDate(m.due_date)}{m.completed_date?` · Completed ${formatDate(m.completed_date)}`:""} · {m.owner}{m.source_label==="demo"?" · demo":""}</small></div>
         <StatusBadge value={`ms-${m.status}`} label={milestoneLabel(m.status)}/>
         <span className="row-actions">
          {m.status!=="completed"&&m.status!=="cancelled"&&<button className="button button-secondary button-small" onClick={()=>setDialog({kind:"milestone",projectId:p.id,milestone:m,markComplete:true})} aria-label={`Mark ${m.title} complete`}>Mark complete</button>}
          <button className="text-button" onClick={()=>setDialog({kind:"milestone",projectId:p.id,milestone:m})} aria-label={`Edit ${m.title}`}>Edit</button>
         </span>
        </li>)}</ul>:<p className="muted">No milestones recorded for this project.</p>}
       </div>
      </td></tr>}
     </Fragment>;
    })}</tbody>
   </table>:<StateMessage title={all.length?"No matching projects":"No projects yet"} detail={all.length?"Try a different search or status.":"Use “Add project” to record the first one."}/>}
  </div>}
  <Dialog open={dialog!==null} title={dialogTitle} onClose={()=>setDialog(null)}>
   {dialog?.kind==="project"&&data&&<ProjectForm project={dialog.project} partners={data.partners} onCancel={()=>setDialog(null)}
     onSaved={saved=>finish(dialog.project?`Saved “${saved.name}”.`:`Added “${saved.name}”.`)}
     onDeleted={dialog.project?()=>finish(`Deleted “${dialog.project!.name}”.`):undefined}/>}
   {dialog?.kind==="milestone"&&<MilestoneForm projectId={dialog.projectId} milestone={dialog.milestone} markComplete={dialog.markComplete} onCancel={()=>setDialog(null)}
     onSaved={saved=>{setExpanded(current=>new Set(current).add(dialog.projectId));finish(dialog.markComplete?`Marked “${saved.title}” complete.`:dialog.milestone?`Saved “${saved.title}”.`:`Added “${saved.title}”.`);}}
     onDeleted={dialog.milestone&&!dialog.markComplete?()=>finish(`Deleted “${dialog.milestone!.title}”.`):undefined}/>}
  </Dialog>
 </>;
}
