import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import StatusBadge from "../../components/ui/StatusBadge";
import { nextStage, stageLabel } from "../../lib/pipeline";
import { formatDate } from "../../lib/utils";
import type { Opportunity } from "../../types";

/** Opportunities table; row actions are shown only when handlers are provided. */
export default function OpportunityTable({ rows, partnerName, onAdvance, onEdit, busyId }: {
  rows: Opportunity[]; partnerName?: (id: string) => string | undefined;
  onAdvance?: (o: Opportunity) => void; onEdit?: (o: Opportunity) => void; busyId?: string | null;
}) {
  const withActions = Boolean(onAdvance || onEdit);
  return <table>
    <thead><tr>
      <th scope="col">Opportunity</th><th scope="col">Stage</th><th scope="col">Owner</th><th scope="col">Next step</th><th scope="col">Updated</th>
      {withActions && <th scope="col"><span className="visually-hidden">Actions</span></th>}
    </tr></thead>
    <tbody>{rows.map((o) => {
      const next = nextStage(o.stage);
      return <tr key={o.id}>
        <td><strong>{o.title}</strong><small>{partnerName ? <Link className="text-link" to={`/partners/${o.partner_id}`}>{partnerName(o.partner_id) ?? o.partner_id}</Link> : o.id}{o.source_label === "demo" ? " · demo" : ""}</small></td>
        <td><StatusBadge value={`stage-${o.stage}`} label={stageLabel(o.stage)} /></td>
        <td>{o.owner}</td>
        <td>{o.next_step || "Not recorded"}<small>{o.next_step_date ? `By ${formatDate(o.next_step_date)}` : "No date set"}</small></td>
        <td>{formatDate(o.updated_at)}</td>
        {withActions && <td className="row-actions">
          {onAdvance && next && <button className="button button-secondary button-small" onClick={() => onAdvance(o)} disabled={busyId === o.id} aria-label={`Move ${o.title} to ${stageLabel(next)}`}>{busyId === o.id ? "Moving…" : <>{stageLabel(next)} <ArrowRight size={13} aria-hidden /></>}</button>}
          {onEdit && <button className="text-button" onClick={() => onEdit(o)} aria-label={`Edit ${o.title}`}>Edit</button>}
        </td>}
      </tr>;
    })}</tbody>
  </table>;
}
