import type { PackageStatus } from "../api/types";

export type Tone = "neutral" | "brand" | "warn" | "danger" | "done";

export const STATUS_META: Record<PackageStatus, { label: string; learnerLabel: string; tone: Tone }> = {
  RECEIVED: { label: "Received", learnerLabel: "Arrived at gate", tone: "neutral" },
  VERIFIED: { label: "Verified", learnerLabel: "Arrived, being stored", tone: "neutral" },
  STORED: { label: "Stored", learnerLabel: "In storage", tone: "neutral" },
  READY_FOR_PICKUP: { label: "Ready for pickup", learnerLabel: "Ready for pickup", tone: "brand" },
  PICKUP_REQUESTED: { label: "Pickup code issued", learnerLabel: "Pickup code issued", tone: "brand" },
  COLLECTED: { label: "Collected", learnerLabel: "Collected", tone: "done" },
  UNIDENTIFIED: { label: "Unidentified", learnerLabel: "Being identified", tone: "warn" },
  DAMAGED: { label: "Held: damaged", learnerLabel: "Held: arrived damaged", tone: "danger" },
  UNDER_INVESTIGATION: { label: "Under investigation", learnerLabel: "Under review", tone: "warn" },
  RETURN_REQUESTED: { label: "Return requested", learnerLabel: "Being returned to courier", tone: "warn" },
  RETURNED: { label: "Returned to courier", learnerLabel: "Returned to courier", tone: "done" },
  LOST: { label: "Lost", learnerLabel: "Reported lost", tone: "danger" },
};

export const ALL_STATUSES = Object.keys(STATUS_META) as PackageStatus[];

export const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-paper text-ink border-line",
  brand: "bg-brand-soft text-brand-strong border-brand/20",
  warn: "bg-warn-soft text-warn border-warn/20",
  danger: "bg-danger-soft text-danger border-danger/20",
  done: "bg-done-soft text-done border-done/20",
};

/** Main path shown on the lifecycle track. Exception states are shown beside it. */
export const HAPPY_PATH: PackageStatus[] = ["RECEIVED", "VERIFIED", "STORED", "READY_FOR_PICKUP", "PICKUP_REQUESTED", "COLLECTED"];
