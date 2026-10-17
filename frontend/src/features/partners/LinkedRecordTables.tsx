import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { RENEWAL, SIGNED_COPY, isWebLink, labelOf } from "../../lib/agreements";
import StateMessage from "../../components/ui/StateMessage";
import StatusBadge from "../../components/ui/StatusBadge";
import type { ActionItem, Agreement, FinanceRecord, Project, ReportRecord } from "../../types";
import { FINANCE_TYPE_LABELS, formatAmount, formatDate, titleCase } from "../../lib/utils";

function Table({ headers, rows, empty }: { headers: string[]; rows: ReactNode[]; empty: string }) {
  if (!rows.length) return <StateMessage title={empty} detail="Nothing is recorded for this partner yet." />;
  return <div className="table-panel inner-table"><table><thead><tr>{headers.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{rows}</tbody></table></div>;
}
const demo = (label?: string) => (label === "demo" ? " · demo" : "");

export function AgreementTable({ rows, partnerName, onEdit, emptyTitle = "No agreements", emptyDetail }: {
  rows: Agreement[]; partnerName?: (id: string) => string | undefined; onEdit?: (a: Agreement) => void; emptyTitle?: string; emptyDetail?: string;
}) {
  if (!rows.length) return <StateMessage title={emptyTitle} detail={emptyDetail ?? "Nothing is recorded for this partner yet."} />;
  return <div className="table-panel inner-table"><table>
    <thead><tr>{["Agreement", "Status", "Signed copy", "Renewal", "Start", "Expiry", "Owner", "Document"].map((h) => <th key={h} scope="col">{h}</th>)}{onEdit && <th scope="col"><span className="visually-hidden">Actions</span></th>}</tr></thead>
    <tbody>{rows.map((a) => <tr key={a.id}>
      <td><strong>{a.title}</strong><small>{partnerName ? <Link className="text-link" to={`/partners/${a.partner_id}`}>{partnerName(a.partner_id) ?? a.partner_id}</Link> : null}{partnerName ? " · " : ""}{a.reference_number ?? "No reference"}{demo(a.source_label)}</small></td>
      <td><StatusBadge value={a.status} /></td>
      <td><StatusBadge value={`signed-${a.signed_copy}`} label={labelOf(SIGNED_COPY, a.signed_copy)} /></td>
      <td>{labelOf(RENEWAL, a.renewal_status)}</td>
      <td>{formatDate(a.start_date)}</td><td>{formatDate(a.expiry_date)}</td><td>{a.owner}</td>
      <td>{isWebLink(a.document_url) ? <a className="text-link" href={a.document_url} target="_blank" rel="noopener noreferrer">Open<span className="visually-hidden"> document for {a.title} (opens in new tab)</span></a> : a.document_url ? "Invalid link" : "None"}</td>
      {onEdit && <td className="row-actions"><button className="text-button" onClick={() => onEdit(a)} aria-label={`Edit ${a.title}`}>Edit</button></td>}
    </tr>)}</tbody>
  </table></div>;
}

export function ProjectTable({ rows, onEdit }: { rows: Project[]; onEdit?: (p: Project) => void }) {
  return <Table headers={["Project", "Status", "Start", "End", "Owner", ...(onEdit ? ["Actions"] : [])]} empty="No projects" rows={rows.map((p) =>
    <tr key={p.id}><td><strong>{p.name}</strong><small>{p.milestone_summary || "No progress note"}{demo(p.source_label)}</small></td><td><StatusBadge value={p.status} /></td><td>{formatDate(p.start_date)}</td><td>{formatDate(p.end_date)}</td><td>{p.owner}</td>
      {onEdit && <td className="row-actions"><button className="text-button" onClick={() => onEdit(p)} aria-label={`Edit ${p.name}`}>Edit</button></td>}</tr>)} />;
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
