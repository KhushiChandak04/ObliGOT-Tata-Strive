import {Link,useParams} from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import StateMessage from "../components/ui/StateMessage";
import StatusBadge from "../components/ui/StatusBadge";
import {ApiError,api} from "../services/functions.service";
import {useResource} from "../lib/useResource";
import {formatDate} from "../lib/utils";
export default function PartnerDetailsPage(){
 const {partnerId=""}=useParams();
 const {data:partner,error,loading,reload}=useResource(()=>api.partners.get(partnerId),[partnerId]);
 const notFound=error instanceof ApiError&&error.status===404;
 return <><PageHeader eyebrow="PARTNER 360" title={partner?.name||"Partner profile"} description="A single view of the relationship and its linked obligations." action={<Link to="/partners" className="button button-secondary">Back to partners</Link>}/>
 {loading&&<StateMessage kind="loading" title="Loading partner record…"/>}
 {!loading&&notFound&&<StateMessage title="Partner not found" detail={`No partner exists with ID “${partnerId}”. It may have been deleted.`}/>}
 {!loading&&error&&!notFound&&<StateMessage kind="error" title="Could not load partner" detail={error.message} action={<button className="button button-secondary" onClick={reload}>Retry</button>}/>}
 {!loading&&partner&&<><div className="panel detail-panel"><div className="detail-heading"><div className="partner-avatar large">{partner.name.slice(0,1)}</div><div><h2>{partner.name}</h2><p>{partner.category} · Owner: {partner.owner}</p></div><StatusBadge value={partner.status}/></div><p>{partner.summary}</p><div className="detail-grid"><div><span>Partner ID</span><strong>{partner.id}</strong></div><div><span>Last updated</span><strong>{formatDate(partner.updated_at)}</strong></div></div>{partner.source_label==="demo"&&<p className="muted">Illustrative demo record — not a verified organization or commitment.</p>}</div><div className="notice"><strong>Next step:</strong><p>Connect agreement, project, finance, reporting, and activity records to complete Partner 360.</p></div></>}
 </>;
}
