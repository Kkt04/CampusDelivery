import { notificationsApi, reportsApi } from "../../api/endpoints";
import type { PackageStatus } from "../../api/types";
import { CountStrip } from "../../components/CountStrip";
import { Button, Card, ErrorAlert, PageHeader, Spinner } from "../../components/ui";
import { STATUS_META, TONE_CLASSES } from "../../lib/status";
import { useAction, useApi } from "../../lib/useApi";

const BAR_ORDER: PackageStatus[] = ["VERIFIED", "STORED", "READY_FOR_PICKUP", "PICKUP_REQUESTED", "UNIDENTIFIED", "DAMAGED",
  "UNDER_INVESTIGATION", "RETURN_REQUESTED"];
const BAR_COLOR: Record<string, string> = { neutral: "bg-muted/40", brand: "bg-brand", warn: "bg-warn", danger: "bg-danger", done: "bg-done" };

export function OpsDashboard() {
  const stats = useApi(() => reportsApi.dashboard(), []);
  const daily = useApi(() => reportsApi.daily(), []);
  const retry = useAction(() => notificationsApi.retryFailed());

  if (stats.loading && !stats.data) return <Spinner label="Loading statistics" />;
  if (stats.error) return <ErrorAlert error={stats.error} onRetry={stats.reload} />;
  const s = stats.data!;
  const custody = BAR_ORDER.reduce((sum, st) => sum + s.by_status[st], 0);
  const utilisation = s.storage_capacity ? Math.round((s.storage_occupied / s.storage_capacity) * 100) : 0;
  const maxDay = Math.max(1, ...(daily.data ?? []).flatMap((d) => [d.received, d.collected]));

  return (
    <div className="space-y-6">
      <PageHeader title="Operations overview" description={`Live figures from the database. Packages count as overdue after ${s.collection_deadline_days} days uncollected.`} />
      <CountStrip items={[
        { label: "Received (all time)", value: s.received, to: "/ops/packages" },
        { label: "In custody", value: s.in_custody },
        { label: "Ready for pickup", value: s.by_status.READY_FOR_PICKUP + s.by_status.PICKUP_REQUESTED, tone: "brand" },
        { label: "Collected", value: s.by_status.COLLECTED },
        { label: "Overdue", value: s.overdue, to: "/ops/exceptions?tab=overdue", tone: "warn" },
        { label: "Unidentified", value: s.by_status.UNIDENTIFIED, to: "/ops/exceptions?tab=unidentified", tone: "warn" },
        { label: "Arrived damaged", value: s.damaged_condition, to: "/ops/exceptions?tab=damaged", tone: "danger" },
      ]} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={`In custody by status (${custody})`}>
          {custody === 0 ? <p className="text-sm text-muted">Nothing in custody.</p> : (
            <>
              <div className="flex h-3 overflow-hidden rounded-full bg-paper" aria-hidden>
                {BAR_ORDER.filter((st) => s.by_status[st] > 0).map((st) => (
                  <div key={st} className={BAR_COLOR[STATUS_META[st].tone]} style={{ width: `${(s.by_status[st] / custody) * 100}%` }} />
                ))}
              </div>
              <ul className="mt-4 grid grid-cols-2 gap-2 text-sm">
                {BAR_ORDER.map((st) => (
                  <li key={st} className="flex items-center justify-between gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${TONE_CLASSES[STATUS_META[st].tone]}`}>{STATUS_META[st].label}</span>
                    <span className="font-semibold">{s.by_status[st]}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>

        <Card title="Storage and follow-ups">
          <p className="text-sm text-muted">Shelf space in use (active locations)</p>
          <div className="mt-2 flex items-center gap-3">
            <div className="h-3 flex-1 overflow-hidden rounded-full bg-paper">
              <div className={`h-full ${utilisation > 85 ? "bg-danger" : "bg-brand"}`} style={{ width: `${utilisation}%` }} />
            </div>
            <span className="text-sm font-semibold">{s.storage_occupied} / {s.storage_capacity}</span>
          </div>
          <dl className="mt-5 grid grid-cols-2 gap-4 text-sm">
            <div><dt className="text-muted">Received today</dt><dd className="text-lg font-bold">{s.received_today}</dd></div>
            <div><dt className="text-muted">Collected today</dt><dd className="text-lg font-bold">{s.collected_today}</dd></div>
            <div><dt className="text-muted">Open incidents</dt><dd className="text-lg font-bold">{s.open_incidents}</dd></div>
            <div><dt className="text-muted">Failed notifications</dt><dd className={`text-lg font-bold ${s.failed_notifications ? "text-danger" : ""}`}>{s.failed_notifications}</dd></div>
          </dl>
          {s.failed_notifications > 0 && (
            <div className="mt-4 space-y-2">
              <ErrorAlert error={retry.error} />
              <Button variant="secondary" pending={retry.pending} onClick={async () => { const r = await retry.run(); if (r) void stats.reload(); }}>
                Retry failed notifications
              </Button>
            </div>
          )}
        </Card>
      </div>

      <Card title="Received and collected, last 14 days">
        {daily.loading ? <Spinner /> : daily.error ? <ErrorAlert error={daily.error} /> : (
          <>
            <div className="flex h-40 items-end gap-1.5 sm:gap-3" role="img" aria-label="Bar chart of packages received and collected per day">
              {daily.data!.map((d) => (
                <div key={d.date} className="flex h-full flex-1 flex-col justify-end" title={`${d.date}: ${d.received} received, ${d.collected} collected`}>
                  <div className="flex h-full items-end justify-center gap-0.5">
                    <div className="w-1/2 max-w-3 rounded-t bg-muted/40" style={{ height: `${(d.received / maxDay) * 100}%` }} />
                    <div className="w-1/2 max-w-3 rounded-t bg-brand" style={{ height: `${(d.collected / maxDay) * 100}%` }} />
                  </div>
                  <p className="mt-1 text-center text-[10px] text-muted">{d.date.slice(8)}</p>
                </div>
              ))}
            </div>
            <div className="mt-3 flex gap-4 text-xs text-muted">
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-muted/40" />Received</span>
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-brand" />Collected</span>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
