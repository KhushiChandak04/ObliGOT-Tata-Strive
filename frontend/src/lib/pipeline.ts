import type { OpportunityStage } from "../types";

/** Lifecycle order; mirrors OPPORTUNITY_STAGES in backend/app/models.py. */
export const STAGES: { id: OpportunityStage; label: string }[] = [
  { id: "identified", label: "Identified" }, { id: "qualification", label: "Qualification" },
  { id: "proposal", label: "Proposal" }, { id: "approval", label: "Approval" },
  { id: "agreement", label: "Agreement / MOU" }, { id: "active", label: "Active" },
  { id: "renewal", label: "Renewal" }, { id: "closed", label: "Closed" },
];

export const stageLabel = (stage: OpportunityStage) => STAGES.find((s) => s.id === stage)?.label ?? stage;

/** The next lifecycle stage, or null once closed. */
export function nextStage(stage: OpportunityStage): OpportunityStage | null {
  const index = STAGES.findIndex((s) => s.id === stage);
  return index >= 0 && index < STAGES.length - 1 ? STAGES[index + 1].id : null;
}
