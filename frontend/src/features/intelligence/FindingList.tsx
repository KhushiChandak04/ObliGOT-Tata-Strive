import StatusBadge from "../../components/ui/StatusBadge";
import type { DeadlineFinding } from "../../types";
import { describeDays, titleCase } from "../../lib/utils";

/** Rule-generated deadline findings with their evidence. Order is the caller's responsibility. */
export default function FindingList({ findings, partnerName, limit }: { findings: DeadlineFinding[]; partnerName?: (id: string) => string | undefined; limit?: number }) {
  const shown = limit ? findings.slice(0, limit) : findings;
  return <div className="action-list">
    {shown.map((f) => <div className="action-row" key={f.id}>
      <span className={`priority-dot ${f.priority}`} aria-hidden />
      <div className="action-copy">
        <strong>{f.issue}</strong>
        <span>{[f.partner_id && partnerName ? partnerName(f.partner_id) ?? f.partner_id : null, ...f.evidence].filter(Boolean).join(" · ")}</span>
      </div>
      <div className="action-meta">
        <StatusBadge value={f.priority} label={`${titleCase(f.priority)} priority`} />
        <small>{f.due_date ? describeDays(f.days_remaining, f.record_type === "agreements") : "No date recorded"}</small>
      </div>
    </div>)}
    {limit && findings.length > limit && <p className="muted panel-footnote">{findings.length - limit} more findings not shown.</p>}
  </div>;
}
