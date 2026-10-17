const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

export function formatDate(value?:string|null):string {
  if (!value) return "Not set";
  // Date-only values ("2026-10-17") are calendar dates; parse them in local time so they never shift a day.
  const parts = DATE_ONLY.exec(value);
  const date = parts ? new Date(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3])) : new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return new Intl.DateTimeFormat("en-IN",{day:"2-digit",month:"short",year:"numeric"}).format(date);
}
export function titleCase(value:string):string { return value.replaceAll("_"," ").replace(/\b\w/g,(char)=>char.toUpperCase()); }
/** "In 5 days", "Due today", "3 days overdue" (or "Expires today", "Expired 3 days ago") from a backend days_remaining value. */
export function describeDays(days?:number|null, isExpiry=false):string {
  if (days === undefined || days === null) return "";
  const plural = (n:number) => `${n} day${n === 1 ? "" : "s"}`;
  if (days === 0) return isExpiry ? "Expires today" : "Due today";
  if (days > 0) return `In ${plural(days)}`;
  return isExpiry ? `Expired ${plural(-days)} ago` : `${plural(-days)} overdue`;
}
/** Formats one stored amount in its own currency. Never used to add amounts together. */
export function formatAmount(amount?:number|null, currency="INR"):string {
  if (amount === undefined || amount === null) return "Not recorded";
  try { return new Intl.NumberFormat("en-IN",{style:"currency",currency,maximumFractionDigits:2}).format(amount); }
  catch { return `${amount.toLocaleString("en-IN")} ${currency}`; }
}
export const FINANCE_TYPE_LABELS:Record<string,string> = {budget:"Budget",fund_received:"Fund received",invoice:"Invoice",utilization_certificate:"Utilization certificate"};
/** Timestamp in the business timezone (IST), e.g. "17 Oct 2026, 3:42 pm". */
export function formatDateTime(value?:string|null):string {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return new Intl.DateTimeFormat("en-IN",{day:"2-digit",month:"short",year:"numeric",hour:"numeric",minute:"2-digit",timeZone:"Asia/Kolkata"}).format(date);
}
