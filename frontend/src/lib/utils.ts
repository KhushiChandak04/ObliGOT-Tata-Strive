export function formatDate(value?:string|null):string {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid date";
  return new Intl.DateTimeFormat("en-IN",{day:"2-digit",month:"short",year:"numeric"}).format(date);
}
export function titleCase(value:string):string { return value.replaceAll("_"," ").replace(/\b\w/g,(char)=>char.toUpperCase()); }
