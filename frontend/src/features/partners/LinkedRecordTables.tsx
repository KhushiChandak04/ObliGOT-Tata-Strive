import type { ReactNode } from "react";
import StateMessage from "../../components/ui/StateMessage";
import StatusBadge from "../../components/ui/StatusBadge";
import type { ActionItem, Agreement, FinanceRecord, Project, ReportRecord } from "../../types";
import { FINANCE_TYPE_LABELS, formatAmount, formatDate, titleCase } from "../../lib/utils";

function Table({ headers, rows, empty }: { headers: string[]; rows: ReactNode[]; empty: string }) {
  if (!rows.length) return <StateMessage title={empty} detail="Nothing is recorded for this partner yet." />;
  return <div className="table-panel inner-table"><table><thead><tr>{headers.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{rows}</tbody></table></div>;
}
const demo = (label?: string) => (label === "demo" ? " · demo" : "");

export function AgreementTable({ rows }: { rows: Agreement[] }) {
  return <Table headers={["Agreement", "Status", "Start", "Expiry", "Owner"]} empty="No agreements" rows={rows.map((a) =>
    <tr key={a.id}><td><strong>{a.title}</strong><small>{a.reference_number ?? "No reference"}{demo(a.source_label)}</small></td><td><StatusBadge value={a.status} /></td><td>{formatDate(a.start_date)}</td><td>{formatDate(a.expiry_date)}</td><td>{a.owner}</td></tr>)} />;
}

export function ProjectTable({ rows }: { rows: Project[] }) {
  return <Table headers={["Project", "Status", "Start", "End", "Owner"]} empty="No projects" rows={rows.map((p) =>
    <tr key={p.id}><td><strong>{p.name}</strong><small>{p.milestone_summary || "No milestone summary"}{demo(p.source_label)}</small></td><td><StatusBadge value={p.status} /></td><td>{formatDate(p.start_date)}</td><td>{formatDate(p.end_date)}</td><td>{p.owner}</td></tr>)} />;
}

export function FinanceTable({ rows }: { rows: FinanceRecord[] }) {
  return <>
    <Table headers={["Record", "Type", "Amount", "Due", "Status"]} empty="No finance records" rows={rows.map((f) =>
      <tr key={f.id}><td><strong>{f.title}</strong><small>{f.reference_number ?? "No reference"}{demo(f.source_label)}</small></td><td>{FINANCE_TYPE_LABELS[f.record_type] ?? f.record_type}</td><td className="numeric">{formatAmount(f.amount, f.currency)}</td><td>{f.record_type === "invoice" || f.record_type === "utilization_certificate" ? formatDate(f.due_date) : "—"}</td><td><StatusBadge value={f.status} /></td></tr>)} />
    {rows.length > 0 && <p className="muted panel-footnote">Amounts are shown per record. Budgets, receipts, invoices, and UCs are different concepts and are not totalled.</p>}
  </>;
}

export function ReportTable({ rows }: { rows: ReportRecord[] }) {
  return <Table headers={["Report", "Type", "Due", "Submitted", "Status", "Owner"]} empty="No reporting obligations" rows={rows.map((r) =>
    <tr key={r.id}><td><strong>{r.title}</strong><small>{r.id}{demo(r.source_label)}</small></td><td>{titleCase(r.report_type)}</td><td>{formatDate(r.due_date)}</td><td>{r.submitted_date ? formatDate(r.submitted_date) : "Not submitted"}</td><td><StatusBadge value={r.status} /></td><td>{r.owner}</td></tr>)} />;
}

export function ActionTable({ rows }: { rows: ActionItem[] }) {
  return <Table headers={["Action", "Priority", "Status", "Due", "Owner"]} empty="No actions" rows={rows.map((a) =>
    <tr key={a.id}><td><strong>{a.title}</strong><small>{a.recommended_action || "No recommended action recorded"}{demo(a.source_label)}</small></td><td><StatusBadge value={a.priority} /></td><td><StatusBadge value={a.status} /></td><td>{formatDate(a.due_date)}</td><td>{a.owner ?? "Unassigned"}</td></tr>)} />;
}
