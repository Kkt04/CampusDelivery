import type { HistoryEntry, PackageStatus } from "../api/types";
import { formatDateTime } from "../lib/format";
import { HAPPY_PATH, STATUS_META } from "../lib/status";

/** Horizontal track of the main lifecycle; an exception state is shown as a branch note. */
export function LifecycleTrack({ status, history, learner }: { status: PackageStatus; history: HistoryEntry[]; learner?: boolean }) {
  const reachedAt = new Map<PackageStatus, string>();
  history.forEach((h) => reachedAt.set(h.to_status, h.created_at));
  const currentIndex = HAPPY_PATH.indexOf(status);
  const lastHappyIndex = Math.max(...HAPPY_PATH.map((s, i) => (reachedAt.has(s) ? i : -1)));
  const offPath = currentIndex === -1;

  return (
    <div>
      <ol className="grid grid-cols-3 gap-y-4 sm:grid-cols-6">
        {HAPPY_PATH.map((step, i) => {
          const done = i <= lastHappyIndex;
          const current = step === status;
          return (
            <li key={step} className="relative pr-2">
              <div className="flex items-center">
                <span className={`z-10 grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 text-[11px] font-bold
                  ${current ? "border-brand bg-brand text-white" : done ? "border-brand bg-brand-soft text-brand-strong" : "border-line bg-white text-muted"}`}>
                  {i + 1}
                </span>
                {i < HAPPY_PATH.length - 1 && <span className={`h-0.5 flex-1 ${i < lastHappyIndex ? "bg-brand" : "bg-line"}`} />}
              </div>
              <p className={`mt-2 text-xs font-semibold ${current ? "text-brand-strong" : done ? "text-ink" : "text-muted"}`}>
                {learner ? STATUS_META[step].learnerLabel : STATUS_META[step].label}
              </p>
              {reachedAt.has(step) && <p className="text-[11px] text-muted">{formatDateTime(reachedAt.get(step))}</p>}
            </li>
          );
        })}
      </ol>
      {offPath && (
        <p className="mt-4 rounded-md border border-warn/30 bg-warn-soft px-3 py-2 text-sm text-warn">
          Currently off the normal path: <strong>{learner ? STATUS_META[status].learnerLabel : STATUS_META[status].label}</strong>
          {reachedAt.has(status) && ` since ${formatDateTime(reachedAt.get(status))}`}.
        </p>
      )}
    </div>
  );
}
