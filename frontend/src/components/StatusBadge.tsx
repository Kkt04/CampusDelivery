import type { PackageStatus } from "../api/types";
import { STATUS_META, TONE_CLASSES } from "../lib/status";

export function StatusBadge({ status, learner = false }: { status: PackageStatus; learner?: boolean }) {
  const meta = STATUS_META[status];
  return (
    <span className={`inline-flex whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${TONE_CLASSES[meta.tone]}`}>
      {learner ? meta.learnerLabel : meta.label}
    </span>
  );
}

export function OverdueFlag() {
  return (
    <span className="inline-flex whitespace-nowrap rounded-full border border-warn/30 px-2 py-0.5 text-xs font-semibold text-warn"
      title="Waiting longer than the collection deadline">
      Overdue
    </span>
  );
}
