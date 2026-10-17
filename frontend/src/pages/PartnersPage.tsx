import {useEffect,useState} from "react";
import {Link} from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import {api} from "../services/functions.service";
import type {Partner} from "../types";
import {titleCase} from "../lib/utils";
export default function PartnersPage(){
 const [partners,setPartners]=useState<Partner[]>([]);const [query,setQuery]=useState("");const [error,setError]=useState("");const [loading,setLoading]=useState(true);
 useEffect(()=>{api.partners().then(setPartners).catch(e=>setError(e instanceof Error?e.message:"API error")).finally(()=>setLoading(false));},[]);
 const filtered=partners.filter(p=>`${p.name} ${p.category} ${p.owner}`.toLowerCase().includes(query.toLowerCase()));
 return <><PageHeader eyebrow="RELATIONSHIP MANAGEMENT" title="Partners" description="Find a partner and inspect the current relationship record."/><div className="toolbar"><input className="search-input" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search partner, category, or owner…" aria-label="Search partners"/><span className="muted">{filtered.length} records</span></div>
 {error&&<StateMessage kind="error" title="Could not load partners" detail={error}/>}
 {loading?<StateMessage kind="loading" title="Loading partners…"/>:<div className="panel table-panel"><table><thead><tr><th>Partner</th><th>Category</th><th>Owner</th><th>Status</th><th></th></tr></thead><tbody>{filtered.map(p=><tr key={p.id}><td><strong>{p.name}</strong><small>{p.id}</small></td><td>{p.category}</td><td>{p.owner}</td><td><span className={`status-pill ${p.status}`}>{titleCase(p.status)}</span></td><td><Link className="text-link" to={`/partners/${p.id}`}>View</Link></td></tr>)}</tbody></table>{filtered.length===0&&<StateMessage title="No matching partners" detail="Try a different search term."/>}</div>}</>;
}
