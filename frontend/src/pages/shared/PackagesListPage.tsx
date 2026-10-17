import { FormEvent, useState } from "react";
import { packagesApi } from "../../api/endpoints";
import type { PackageStatus } from "../../api/types";
import { PackageTable } from "../../components/PackageTable";
import { Button, Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from "../../components/ui";
import { ALL_STATUSES, STATUS_META } from "../../lib/status";
import { useApi } from "../../lib/useApi";

const CUSTODY: PackageStatus[] = ["RECEIVED", "VERIFIED", "STORED", "READY_FOR_PICKUP", "PICKUP_REQUESTED", "UNIDENTIFIED",
  "DAMAGED", "UNDER_INVESTIGATION", "RETURN_REQUESTED"];
const PAGE_SIZE = 20;

interface Props { title: string; description: string; basePath: string; defaultScope: "custody" | "all" }

export function PackagesListPage({ title, description, basePath, defaultScope }: Props) {
  const [draft, setDraft] = useState({ q: "", status: "" as "" | PackageStatus, overdue: false, from: "", to: "" });
  const [filters, setFilters] = useState(draft);
  const [page, setPage] = useState(1);

  const statuses = filters.status ? [filters.status] : defaultScope === "custody" ? CUSTODY : [];
  const list = useApi(
    () => packagesApi.list({ q: filters.q || undefined, status: statuses, overdue: filters.overdue,
      arrived_from: filters.from || undefined, arrived_to: filters.to || undefined, page, page_size: PAGE_SIZE }),
    [filters, page, defaultScope],
  );

  function onSearch(e: FormEvent) {
    e.preventDefault();
    setPage(1);
    setFilters(draft);
  }

  return (
    <div>
      <PageHeader title={title} description={description} />
      <form onSubmit={onSearch} className="card mb-4 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr_auto] lg:items-end">
        <div>
          <label htmlFor="q" className="label">Search</label>
          <input id="q" className="input" placeholder="Code, tracking ID, courier, learner" value={draft.q}
            onChange={(e) => setDraft({ ...draft, q: e.target.value })} />
        </div>
        <div>
          <label htmlFor="status" className="label">Status</label>
          <select id="status" className="input" value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value as PackageStatus | "" })}>
            <option value="">{defaultScope === "custody" ? "All in custody" : "Any status"}</option>
            {(defaultScope === "custody" ? CUSTODY : ALL_STATUSES).map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="from" className="label">Arrived from</label>
          <input id="from" type="date" className="input" value={draft.from} onChange={(e) => setDraft({ ...draft, from: e.target.value })} />
        </div>
        <div>
          <label htmlFor="to" className="label">Arrived to</label>
          <input id="to" type="date" className="input" value={draft.to} onChange={(e) => setDraft({ ...draft, to: e.target.value })} />
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 whitespace-nowrap text-sm">
            <input type="checkbox" className="h-4 w-4 accent-brand" checked={draft.overdue} onChange={(e) => setDraft({ ...draft, overdue: e.target.checked })} />
            Overdue only
          </label>
          <Button type="submit">Search</Button>
        </div>
      </form>

      <Card bodyClass="p-0">
        {list.loading && !list.data ? <div className="px-5"><Spinner label="Loading packages" /></div>
          : list.error ? <div className="p-5"><ErrorAlert error={list.error} onRetry={list.reload} /></div>
          : list.data && list.data.items.length === 0 ? (
            <EmptyState title="No packages match">Try a shorter search, or clear the status and date filters.</EmptyState>
          ) : list.data && (
            <>
              <PackageTable packages={list.data.items} basePath={basePath} />
              <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPage={setPage} />
            </>
          )}
      </Card>
    </div>
  );
}
