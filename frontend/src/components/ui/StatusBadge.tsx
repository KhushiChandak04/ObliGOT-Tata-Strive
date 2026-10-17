import { titleCase } from "../../lib/utils";

/** Text label plus colour; the CSS tone is the value itself (see .status-pill.* in index.css). */
export default function StatusBadge({ value, label }: { value: string; label?: string }) {
  return <span className={`status-pill ${value}`}>{label ?? titleCase(value)}</span>;
}
