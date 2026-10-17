import {useEffect,useState} from "react";
import {Link,useParams} from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import {api} from "../services/functions.service";
import type {Partner} from "../types";
import {titleCase} from "../lib/utils";
export default function PartnerDetailsPage(){
 const {partnerId=""}=useParams();const [partner,setPartner]=useState<Partner|null>(null);const [error,setError]=useState("");const [loading,setLoading]=useState(true);
 useEffect(()=>{api.partners().then(rows=>setPartner(rows.find(p=>p.id===partnerId)||null)).catch(e=>setError(e instanceof Error?e.message:"API error")).finally(()=>setLoading(false));},[partnerId]);
 return <><PageHeader eyebrow="PARTNER 360" title={partner?.name||"Partner profile"} description="A single view of the relationship and its linked obligations." action={<Link to="/partners" className="button button-secondary">Back to partners</Link>}/>
 {error&&<StateMessage kind="error" title="Could not load partner" detail={error}/>}
 {loading&&<StateMessage kind="loading" title="Loading partner record…"/>}
 {!loading&&!error&&!partner&&<StateMessage title="Partner not found" detail="The requested record does not exist in the demo API."/>}
 {partner&&<><div className="panel detail-panel"><div className="detail-heading"><div className="partner-avatar large">{partner.name.slice(0,1)}</div><div><h2>{partner.name}</h2><p>{partner.category} · Owner: {partner.owner}</p></div><span className={`status-pill ${partner.status}`}>{titleCase(partner.status)}</span></div><p>{partner.summary}</p><div className="detail-grid"><div><span>Partner ID</span><strong>{partner.id}</strong></div><div><span>Last updated</span><strong>{partner.updated_at}</strong></div></div></div><div className="notice"><strong>Next step:</strong><p>Connect agreement, project, finance, reporting, and activity records to complete Partner 360.</p></div></>}
 </>;
}
