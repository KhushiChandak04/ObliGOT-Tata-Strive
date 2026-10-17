import { ChevronRight } from "lucide-react";
import StatusBadge from "../../components/ui/StatusBadge";
import { CATEGORY_LABELS, DECISION_LABELS, alertTiming } from "../../lib/alerts";
import { titleCase } from "../../lib/utils";
import type { Alert } from "../../types";

/** Alert rows; each row is a button that opens the alert detail. `ranked` numbers the rows (Today's 5). */
export default function AlertList({ alerts, partnerName, onOpen, ranked = false }: {
  alerts: Alert[]; partnerName?: (id: string) => string | undefined; onOpen: (alert: Alert) => void; ranked?: boolean;
}) {
  return <ol className={`alert-list${ranked ? " ranked" : ""}`}>
    {alerts.map((alert, index) => {
      const partner = alert.partner_id ? partnerName?.(alert.partner_id) ?? alert.partner_id : null;
      return <li key={alert.id}>
        <button className="alert-row" onClick={() => onOpen(alert)} aria-label={`${alert.rule_title}: ${alert.record_title}. ${titleCase(alert.priority.level)} priority, score ${alert.priority.score}. Open details`}>
          {ranked ? <span className="alert-rank" aria-hidden>{index + 1}</span> : <span className={`priority-dot ${alert.priority.level}`} aria-hidden />}
          <span className="alert-copy">
            <strong>{alert.rule_title}: {alert.record_title}</strong>
            <span>{[partner, CATEGORY_LABELS[alert.category], `Owner: ${alert.owner}`].filter(Boolean).join(" · ")}</span>
            <span className="alert-action-hint">Next: {alert.recommended_action}</span>
          </span>
          <span className="alert-meta">
            <StatusBadge value={alert.priority.level} label={`${titleCase(alert.priority.level)} · ${alert.priority.score}`} />
            <small>{alertTiming(alert)}</small>
            {alert.review && <small className="review-tag">{DECISION_LABELS[alert.review.decision]}</small>}
          </span>
          <ChevronRight size={15} className="alert-chevron" aria-hidden />
        </button>
      </li>;
    })}
  </ol>;
}
