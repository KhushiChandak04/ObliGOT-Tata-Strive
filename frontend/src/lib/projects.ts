import type { MilestoneStatus, RecordStatus } from "../types";

// Mirrors RecordStatus and MilestoneStatus in backend/app/models.py.
export const PROJECT_STATUSES: { id: RecordStatus; label: string }[] = [
  { id: "planned", label: "Planned" }, { id: "active", label: "Active" }, { id: "on_hold", label: "On hold" },
  { id: "completed", label: "Completed" }, { id: "closed", label: "Closed" },
];
export const MILESTONE_STATUSES: { id: MilestoneStatus; label: string }[] = [
  { id: "planned", label: "Planned" }, { id: "in_progress", label: "In progress" }, { id: "completed", label: "Completed" },
  { id: "missed", label: "Missed" }, { id: "cancelled", label: "Cancelled" },
];
