import { Link } from "react-router-dom";
import { notificationsApi, packagesApi } from "../../api/endpoints";
import type { Package } from "../../api/types";
import { useUser } from "../../auth/AuthContext";
import { OverdueFlag, StatusBadge } from "../../components/StatusBadge";
import { Card, EmptyState, ErrorAlert, PageHeader, Spinner, TextLink } from "../../components/ui";
import { formatDateTime, timeAgo } from "../../lib/format";
import { useApi } from "../../lib/useApi";

export function LearnerDashboard() {
  const user = useUser();
  const ready = useApi(() => packagesApi.list({ status: ["READY_FOR_PICKUP", "PICKUP_REQUESTED"], page_size: 10 }), []);
  const onTheWay = useApi(() => packagesApi.list({
    status: ["RECEIVED", "VERIFIED", "STORED", "DAMAGED", "UNDER_INVESTIGATION", "RETURN_REQUESTED"], page_size: 10 }), []);
  const notes = useApi(() => notificationsApi.list(1), []);

  return (
    <div className="space-y-8">
      <PageHeader title={`Hello, ${user.full_name.split(" ")[0]}`} description="Packages addressed to you at Gate No. 2." />

      <section>
        <h2 className="mb-3 text-lg font-semibold">Ready to collect</h2>
        {ready.loading ? <Spinner /> : ready.error ? <ErrorAlert error={ready.error} onRetry={ready.reload} />
          : ready.data!.items.length === 0 ? (
            <div className="card"><EmptyState title="Nothing to collect right now">When security puts a package on the shelf for you, it shows up here and you get a notification.</EmptyState></div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {ready.data!.items.map((p) => <ReadyCard key={p.id} pkg={p} />)}
            </div>
          )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Arrived, not ready yet" bodyClass="p-0">
          {onTheWay.loading ? <div className="px-5"><Spinner /></div> : onTheWay.error ? <div className="p-5"><ErrorAlert error={onTheWay.error} /></div>
            : onTheWay.data!.items.length === 0 ? <p className="px-5 py-6 text-sm text-muted">No packages in progress.</p> : (
              <ul className="divide-y divide-line">
                {onTheWay.data!.items.map((p) => (
                  <li key={p.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                    <Link to={`/learner/packages/${p.id}`} className="min-w-0">
                      <p className="code-text text-brand-strong">{p.internal_code}</p>
                      <p className="text-muted">{p.courier_name}, arrived {formatDateTime(p.arrived_at)}</p>
                    </Link>
                    <StatusBadge status={p.status} learner />
                  </li>
                ))}
              </ul>
            )}
        </Card>
        <Card title="Latest notifications" actions={<TextLink to="/notifications">See all</TextLink>} bodyClass="p-0">
          {notes.loading ? <div className="px-5"><Spinner /></div> : notes.error ? <div className="p-5"><ErrorAlert error={notes.error} /></div>
            : notes.data!.items.length === 0 ? <p className="px-5 py-6 text-sm text-muted">No notifications yet.</p> : (
              <ul className="divide-y divide-line">
                {notes.data!.items.slice(0, 4).map((n) => (
                  <li key={n.id} className="px-5 py-3 text-sm">
                    <p className="font-semibold">{n.title} <span className="font-normal text-muted">{timeAgo(n.created_at)}</span></p>
                    <p className="text-muted">{n.message}</p>
                  </li>
                ))}
              </ul>
            )}
        </Card>
      </div>
    </div>
  );
}

function ReadyCard({ pkg }: { pkg: Package }) {
  return (
    <div className="card flex flex-col justify-between gap-4 p-5">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={pkg.status} learner />
          {pkg.is_overdue && <OverdueFlag />}
        </div>
        <p className="code-text mt-3 text-lg">{pkg.internal_code}</p>
        <p className="text-sm text-muted">{pkg.courier_name}, shelf <strong className="text-ink">{pkg.storage_location?.code}</strong></p>
        {pkg.is_overdue && <p className="mt-2 text-sm text-warn">Please collect soon: this package is past the collection deadline.</p>}
      </div>
      <div className="flex gap-3">
        <Link to={`/learner/packages/${pkg.id}/pickup`} className="rounded-md bg-brand px-3.5 py-2 text-sm font-semibold text-white hover:bg-brand-strong">
          Get pickup code
        </Link>
        <Link to={`/learner/packages/${pkg.id}`} className="rounded-md px-3.5 py-2 text-sm font-semibold text-brand-strong hover:bg-brand-soft">Details</Link>
      </div>
    </div>
  );
}
