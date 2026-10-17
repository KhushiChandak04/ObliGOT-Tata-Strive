import {useState} from "react";
import {Plus} from "lucide-react";
import {Link,useNavigate} from "react-router-dom";
import Dialog from "../components/ui/Dialog";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import StatusBadge from "../components/ui/StatusBadge";
import PartnerForm from "../features/partners/PartnerForm";
import {api} from "../services/functions.service";
import {useResource} from "../lib/useResource";
import {titleCase} from "../lib/utils";
import type {PartnerStatus} from "../types";

const STATUS_FILTERS:(PartnerStatus|"all")[]=["all","prospect","qualification","active","on_hold","closed"];

export default function PartnersPage(){
 const {data,error,loading,reload}=useResource(()=>api.partners.list(),[]);
 const [query,setQuery]=useState("");
 const [status,setStatus]=useState<PartnerStatus|"all">("all");
 const [creating,setCreating]=useState(false);
 const navigate=useNavigate();
 const partners=data??[];
 const filtered=partners.filter(p=>(status==="all"||p.status===status)&&`${p.name} ${p.category} ${p.owner}`.toLowerCase().includes(query.trim().toLowerCase()));
 const filtersActive=query.trim()!==""||status!=="all";
 return <><PageHeader eyebrow="RELATIONSHIP MANAGEMENT" title="Partners" description="Find a partner and inspect the current relationship record." action={<button className="button button-primary" onClick={()=>setCreating(true)}><Plus size={15} aria-hidden/> Add partner</button>}/>
 <div className="toolbar">
  <input className="search-input" type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search partner, category, or owner…" aria-label="Search partners"/>
  <label className="toolbar-select"><span>Status</span><select value={status} onChange={e=>setStatus(e.target.value as PartnerStatus|"all")}>{STATUS_FILTERS.map(s=><option key={s} value={s}>{s==="all"?"All statuses":titleCase(s)}</option>)}</select></label>
  <span className="muted" aria-live="polite">{loading?"":`${filtered.length} of ${partners.length} partners`}</span>
  {filtersActive&&<button className="text-button" onClick={()=>{setQuery("");setStatus("all");}}>Clear filters</button>}
 </div>
 {error&&<StateMessage kind="error" title="Could not load partners" detail={error.message} action={<button className="button button-secondary" onClick={reload}>Retry</button>}/>}
 {loading?<StateMessage kind="loading" title="Loading partners…"/>:!error&&<div className="panel table-panel"><table><thead><tr><th scope="col">Partner</th><th scope="col">Category</th><th scope="col">Owner</th><th scope="col">Status</th><th scope="col"><span className="visually-hidden">Actions</span></th></tr></thead><tbody>{filtered.map(p=><tr key={p.id}><td><strong>{p.name}</strong><small>{p.id}{p.source_label==="demo"?" · demo":""}</small></td><td>{p.category}</td><td>{p.owner}</td><td><StatusBadge value={p.status}/></td><td><Link className="text-link" to={`/partners/${p.id}`} aria-label={`Open ${p.name}`}>Open</Link></td></tr>)}</tbody></table>{filtered.length===0&&<StateMessage title={partners.length?"No matching partners":"No partner records yet"} detail={partners.length?"Try a different search term or status.":"Use “Add partner” to create the first record."}/>}</div>}
 <Dialog open={creating} title="Add partner" onClose={()=>setCreating(false)}>
  <PartnerForm onCancel={()=>setCreating(false)} onSaved={saved=>{setCreating(false);navigate(`/partners/${saved.id}`);}}/>
 </Dialog>
 </>;
}
