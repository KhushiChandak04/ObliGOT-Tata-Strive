import {useState} from "react";
import {Link} from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import StatusBadge from "../components/ui/StatusBadge";
import {api} from "../services/functions.service";
import {useResource} from "../lib/useResource";
export default function PartnersPage(){
 const {data,error,loading,reload}=useResource(()=>api.partners.list(),[]);
 const [query,setQuery]=useState("");
 const partners=data??[];
 const filtered=partners.filter(p=>`${p.name} ${p.category} ${p.owner}`.toLowerCase().includes(query.toLowerCase()));
 return <><PageHeader eyebrow="RELATIONSHIP MANAGEMENT" title="Partners" description="Find a partner and inspect the current relationship record."/><div className="toolbar"><input className="search-input" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search partner, category, or owner…" aria-label="Search partners"/><span className="muted">{filtered.length} records</span></div>
 {error&&<StateMessage kind="error" title="Could not load partners" detail={error.message} action={<button className="button button-secondary" onClick={reload}>Retry</button>}/>}
 {loading?<StateMessage kind="loading" title="Loading partners…"/>:!error&&<div className="panel table-panel"><table><thead><tr><th>Partner</th><th>Category</th><th>Owner</th><th>Status</th><th><span className="visually-hidden">Actions</span></th></tr></thead><tbody>{filtered.map(p=><tr key={p.id}><td><strong>{p.name}</strong><small>{p.id}{p.source_label==="demo"?" · demo":""}</small></td><td>{p.category}</td><td>{p.owner}</td><td><StatusBadge value={p.status}/></td><td><Link className="text-link" to={`/partners/${p.id}`} aria-label={`View ${p.name}`}>View</Link></td></tr>)}</tbody></table>{filtered.length===0&&<StateMessage title={partners.length?"No matching partners":"No partner records yet"} detail={partners.length?"Try a different search term.":"Partners added through the API will appear here."}/>}</div>}</>;
}
