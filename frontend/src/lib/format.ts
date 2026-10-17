const dateTime = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const dateOnly = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric" });

export const formatDateTime = (iso: string | null | undefined) => (iso ? dateTime.format(new Date(iso)) : "–");
export const formatDate = (iso: string | null | undefined) => (iso ? dateOnly.format(new Date(iso)) : "–");

export function timeAgo(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export const sentenceCase = (value: string) =>
  value.charAt(0).toUpperCase() + value.slice(1).toLowerCase().replace(/_/g, " ");

export const isoDay = (d: Date) => d.toISOString().slice(0, 10);
