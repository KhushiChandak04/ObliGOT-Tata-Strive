/** Only http(s) links are rendered; anything else (e.g. javascript:) is shown as plain text. */
export function isWebLink(url?: string | null): url is string {
  return Boolean(url && /^https?:\/\//i.test(url.trim()));
}
