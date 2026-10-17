import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { packagesApi, type PackageQuery } from "../../api/endpoints";
import { PackageTable } from "../../components/PackageTable";
import { Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from "../../components/ui";
import { useApi } from "../../lib/useApi";

const TABS: { key: string; label: string; query: PackageQuery; empty: string }[] = [
  { key: "overdue", label: "Overdue", query: { overdue: true }, empty: "No package is past the collection deadline." },
  { key: "unidentified", label: "Unidentified", query: { status: ["UNIDENTIFIED"] }, empty: "Every package has a recipient." },
  { key: "damaged", label: "Damaged", query: { condition: "DAMAGED" }, empty: "No damaged packages recorded." },
  { key: "investigation", label: "Investigations", query: { status: ["UNDER_INVESTIGATION"] }, empty: "Nothing under investigation." },
  { key: "returns", label: "Returns", query: { status: ["RETURN_REQUESTED"] }, empty: "No returns waiting for the courier." },
];

export function ExceptionsPage() {
  const [params, setParams] = useSearchParams();
  const tab = TABS.find((t) => t.key === params.get("tab")) ?? TABS[0];
  const [page, setPage] = useState(1);
  const list = useApi(() => packagesApi.list({ ...tab.query, page, page_size: 20 }), [tab.key, page]);

  return (
    <div>
      <PageHeader title="Needs attention" description="Overdue, unidentified, damaged and other packages that need a decision. Open one to act on it." />
      <div className="mb-4 flex flex-wrap gap-1 rounded-md border border-line bg-white p-1 sm:w-fit" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={t.key === tab.key}
            className={`rounded px-3 py-1.5 text-sm font-semibold ${t.key === tab.key ? "bg-brand-soft text-brand-strong" : "text-muted"}`}
            onClick={() => { setParams({ tab: t.key }); setPage(1); }}>
            {t.label}
          </button>
        ))}
      </div>
      <Card bodyClass="p-0">
        {list.loading && !list.data ? <div className="px-5"><Spinner /></div>
          : list.error ? <div className="p-5"><ErrorAlert error={list.error} onRetry={list.reload} /></div>
          : list.data!.items.length === 0 ? <EmptyState title={tab.empty} />
          : (
            <>
              <PackageTable packages={list.data!.items} basePath="/ops/packages" />
              <Pagination page={page} pageSize={20} total={list.data!.total} onPage={setPage} />
            </>
          )}
      </Card>
    </div>
  );
}
