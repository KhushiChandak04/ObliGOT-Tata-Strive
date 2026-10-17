export type PipelineStage = "Opportunity" | "Qualification" | "Proposal" | "Approval" | "MOU" | "Implementation" | "Renewal" | "Closure";
export type RecordStatus = "Active" | "Pending" | "Submitted" | "Overdue" | "Paid" | "Draft" | "Planned" | "In progress" | "Complete";

export interface PipelineItem { id: string; partner: string; owner: string; stage: PipelineStage; nextAction: string; dueDate: string; source_label: "demo"; }
export interface Agreement { id: string; partner: string; reference: string; status: "Active" | "Expired" | "Draft"; startDate: string; endDate: string; signedCopy: "Available" | "Missing"; owner: string; renewal: "Not recorded" | "In discussion" | "Renewed"; source_label: "demo"; }
export interface Milestone { id: string; title: string; dueDate: string; status: "Complete" | "In progress" | "Overdue"; }
export interface Project { id: string; name: string; partner: string; status: "Active" | "Planned" | "Complete"; owner: string; startDate: string; endDate: string; milestones: Milestone[]; source_label: "demo"; }
export interface Budget { id: string; partner: string; project: string; amount: number; currency: "INR"; status: "Planned" | "Approved"; }
export interface FundReceived { id: string; partner: string; project: string; amount: number; currency: "INR"; receivedDate: string; status: "Received" | "Expected"; }
export interface Invoice { id: string; partner: string; invoiceDate: string; dueDate: string | null; amount: number; currency: "INR"; status: "Draft" | "Sent" | "Paid"; }
export interface Report { id: string; type: "Quarterly Progress" | "Impact" | "Utilization Certificate"; partner: string; project: string; dueDate: string; status: "Pending" | "Submitted" | "Overdue"; owner: string; }

const daysFromToday = (days: number): string => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
};

export const pipelineItems: PipelineItem[] = [
  { id: "P-001", partner: "Kaveri Retail Academy", owner: "Rahul S.", stage: "Renewal", nextAction: "Schedule renewal call", dueDate: daysFromToday(7), source_label: "demo" },
  { id: "P-002", partner: "Greenleaf Skills Foundation", owner: "Anita R.", stage: "Implementation", nextAction: "Review quarterly plan", dueDate: daysFromToday(4), source_label: "demo" },
  { id: "P-003", partner: "Sahyadri Agro Trust", owner: "Meera K.", stage: "Proposal", nextAction: "Send revised proposal", dueDate: daysFromToday(12), source_label: "demo" },
  { id: "P-004", partner: "Northgate Logistics", owner: "Rahul S.", stage: "Qualification", nextAction: "Confirm programme scope", dueDate: daysFromToday(16), source_label: "demo" },
];

export const agreements: Agreement[] = [
  { id: "AGR-001", partner: "Kaveri Retail Academy", reference: "MOU/KRA/2025/014", status: "Active", startDate: daysFromToday(-350), endDate: daysFromToday(14), signedCopy: "Available", owner: "Rahul S.", renewal: "Not recorded", source_label: "demo" },
  { id: "AGR-002", partner: "Greenleaf Skills Foundation", reference: "MOU/GSF/2025/009", status: "Active", startDate: daysFromToday(-220), endDate: daysFromToday(42), signedCopy: "Available", owner: "Anita R.", renewal: "In discussion", source_label: "demo" },
  { id: "AGR-003", partner: "Lotus Healthcare Skills", reference: "MOU/LHS/2024/021", status: "Active", startDate: daysFromToday(-490), endDate: daysFromToday(78), signedCopy: "Missing", owner: "Anita R.", renewal: "Not recorded", source_label: "demo" },
];

export const projects: Project[] = [
  { id: "PRJ-001", name: "Retail Readiness Cohort 4", partner: "Kaveri Retail Academy", status: "Active", owner: "Rahul S.", startDate: daysFromToday(-120), endDate: daysFromToday(80), milestones: [{ id: "M-1", title: "Mobilization", dueDate: daysFromToday(-60), status: "Complete" }, { id: "M-2", title: "Cohort 4 placements", dueDate: daysFromToday(18), status: "In progress" }], source_label: "demo" },
  { id: "PRJ-002", name: "Agri Skilling Cohort 3", partner: "Sahyadri Agro Trust", status: "Active", owner: "Meera K.", startDate: daysFromToday(-180), endDate: daysFromToday(30), milestones: [{ id: "M-3", title: "Training delivery", dueDate: daysFromToday(-21), status: "Overdue" }, { id: "M-4", title: "Impact report", dueDate: daysFromToday(12), status: "In progress" }] , source_label: "demo" },
];

export const budgets: Budget[] = [{ id: "B-001", partner: "Kaveri Retail Academy", project: "Retail Readiness Cohort 4", amount: 1250000, currency: "INR", status: "Approved" }, { id: "B-002", partner: "Greenleaf Skills Foundation", project: "Digital Skills Bridge", amount: 900000, currency: "INR", status: "Planned" }];
export const fundsReceived: FundReceived[] = [{ id: "F-001", partner: "Kaveri Retail Academy", project: "Retail Readiness Cohort 4", amount: 750000, currency: "INR", receivedDate: daysFromToday(-45), status: "Received" }, { id: "F-002", partner: "Greenleaf Skills Foundation", project: "Digital Skills Bridge", amount: 400000, currency: "INR", receivedDate: daysFromToday(14), status: "Expected" }];
export const invoices: Invoice[] = [{ id: "INV-001", partner: "Northgate Logistics", invoiceDate: daysFromToday(-35), dueDate: daysFromToday(-5), amount: 180000, currency: "INR", status: "Sent" }, { id: "INV-002", partner: "Lotus Healthcare Skills", invoiceDate: daysFromToday(-20), dueDate: null, amount: 220000, currency: "INR", status: "Draft" }];
export const reports: Report[] = [{ id: "R-001", type: "Quarterly Progress", partner: "Greenleaf Skills Foundation", project: "Digital Skills Bridge", dueDate: daysFromToday(-9), status: "Overdue", owner: "Anita R." }, { id: "R-002", type: "Utilization Certificate", partner: "Sahyadri Agro Trust", project: "Agri Skilling Cohort 3", dueDate: daysFromToday(-21), status: "Pending", owner: "Meera K." }, { id: "R-003", type: "Impact", partner: "Kaveri Retail Academy", project: "Retail Readiness Cohort 4", dueDate: daysFromToday(25), status: "Submitted", owner: "Rahul S." }];

export const repository = { pipeline: pipelineItems, agreements, projects, budgets, fundsReceived, invoices, reports };
