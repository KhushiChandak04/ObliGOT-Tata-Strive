import type { Alert, AlertCategory, AlertSeverity, ReviewDecision } from "../types";

export const CATEGORY_LABELS: Record<AlertCategory, string> = {
  agreements: "Agreements", pipeline: "Pipeline", projects: "Projects & milestones", reporting: "Reporting",
  finance: "Finance", tasks: "Tasks", data_quality: "Data quality",
};
export const SEVERITY_LABELS: Record<AlertSeverity, string> = {
  overdue: "Overdue", risk: "Risk", due_soon: "Due soon", missing_data: "Missing data",
};
export const DECISION_LABELS: Record<ReviewDecision, string> = {
  acknowledged: "Acknowledged", deferred: "Deferred", dismissed: "Dismissed", task_created: "Task created",
};

/** Plain-language timing from the backend's days_remaining (the browser does no date arithmetic). */
export function alertTiming(alert: Alert): string {
  const days = alert.days_remaining;
  if (days === null || days === undefined) return alert.severity === "missing_data" ? "Date missing" : "No date";
  const isExpiry = alert.rule_id.startsWith("MOU_");
  const plural = (n: number) => `${n} day${n === 1 ? "" : "s"}`;
  if (days === 0) return isExpiry ? "Expires today" : "Due today";
  if (days > 0) return isExpiry ? `Expires in ${plural(days)}` : `Due in ${plural(days)}`;
  return isExpiry ? `Expired ${plural(-days)} ago` : `${plural(-days)} overdue`;
}

export const TODAY_COUNT = 5;
/** Today's 5: the highest-priority active alerts (API order) that nobody has turned into a task yet. */
export function todaysAlerts(alerts: Alert[]): Alert[] {
  return alerts.filter((a) => !a.hidden_by_review && a.review?.decision !== "task_created").slice(0, TODAY_COUNT);
}
