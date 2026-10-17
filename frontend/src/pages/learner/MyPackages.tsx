import { useState } from "react";
import { Link } from "react-router-dom";
import { packagesApi } from "../../api/endpoints";
import type { PackageStatus } from "../../api/types";
import { OverdueFlag, StatusBadge } from "../../components/StatusBadge";
import { Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { useApi } from "../../lib/useApi";

const TABS: { key: string; label: string; statuses: PackageStatus[] }[] = [
  { key: "open", label: "Active", statuses: ["RECEIVED", "VERIFIED", "STORED", "READY_FOR_PICKUP", "PICKUP_REQUESTED", "DAMAGED", "UNDER_INVESTIGATION", "RETURN_REQUESTED"] },
  { key: "closed", label: "Closed", statuses: ["COLLECTED", "RETURNED", "LOST"] },
];

export function MyPackages() {
  const [tab, setTab] = useState(TABS[0]);
  const [page, setPage] = useState(1);
  const list = useApi(() => packagesApi.list({ status: tab.statuses, page, page_size: 15 }), [tab, page]);

  return (
    <div>
      <PageHeader title="My packages" description="Only packages addressed to your account are shown." />
      <div className="mb-4 flex gap-1 rounded-md border border-line bg-white p-1 sm:w-fit" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab.key === t.key}
            className={`flex-1 rounded px-4 py-1.5 text-sm font-semibold sm:flex-none ${tab.key === t.key ? "bg-brand-soft text-brand-strong" : "text-muted"}`}
            onClick={() => { setTab(t); setPage(1); }}>
            {t.label}
          </button>
        ))}
      </div>
      <Card bodyClass="p-0">
        {list.loading && !list.data ? <div className="px-5"><Spinner /></div>
          : list.error ? <div className="p-5"><ErrorAlert error={list.error} onRetry={list.reload} /></div>
          : list.data!.items.length === 0 ? <EmptyState title={tab.key === "open" ? "No active packages" : "No closed packages yet"} />
          : (
            <>
              <ul className="divide-y divide-line">
                {list.data!.items.map((p) => (
                  <li key={p.id}>
                    <Link to={`/learner/packages/${p.id}`} className="flex flex-col gap-2 px-5 py-4 hover:bg-paper/70 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="code-text text-brand-strong">{p.internal_code}</p>
                        <p className="text-sm text-muted">{p.courier_name}, arrived {formatDateTime(p.arrived_at)}</p>
                      </div>
                      <div className="flex gap-2"><StatusBadge status={p.status} learner />{p.is_overdue && <OverdueFlag />}</div>
                    </Link>
                  </li>
                ))}
              </ul>
              <Pagination page={page} pageSize={15} total={list.data!.total} onPage={setPage} />
            </>
          )}
      </Card>
    </div>
  );
}
