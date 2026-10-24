import { useState } from "react";
import { Link } from "react-router-dom";
import { packagesApi } from "../../api/endpoints";
import type { PackageStatus } from "../../api/types";
import { OverdueFlag, StatusBadge } from "../../components/StatusBadge";
import { Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatDateTime } from "../../lib/format";
import { useApi } from "../../lib/useApi";

export function MyPackages() {
  const { t } = useLanguage();
  const [tabKey, setTabKey] = useState<"open" | "closed">("open");
  const [page, setPage] = useState(1);

  const tabs: { key: "open" | "closed"; label: string; statuses: PackageStatus[] }[] = [
    {
      key: "open",
      label: t("tabIncoming"),
      statuses: [
        "RECEIVED", "VERIFIED", "STORED", "READY_FOR_PICKUP", "PICKUP_REQUESTED",
        "DAMAGED", "UNDER_INVESTIGATION", "RETURN_REQUESTED",
      ],
    },
    {
      key: "closed",
      label: t("tabCollected"),
      statuses: ["COLLECTED", "RETURNED", "LOST"],
    },
  ];

  const currentTab = tabs.find((t) => t.key === tabKey) || tabs[0];
  const list = useApi(() => packagesApi.list({ status: currentTab.statuses, page, page_size: 15 }), [tabKey, page]);

  return (
    <div>
      <PageHeader title={t("myPackagesTitle")} description={t("myPackagesSubtitle")} />
      <div className="mb-4 flex gap-1 rounded-xl border border-line bg-white p-1 sm:w-fit" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={tabKey === tab.key}
            className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition sm:flex-none ${
              tabKey === tab.key ? "bg-primary-50 text-primary-700 shadow-sm" : "text-muted hover:text-ink"
            }`}
            onClick={() => {
              setTabKey(tab.key);
              setPage(1);
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <Card bodyClass="p-0">
        {list.loading && !list.data ? (
          <div className="px-5 py-6">
            <Spinner label={t("loading")} />
          </div>
        ) : list.error ? (
          <div className="p-5">
            <ErrorAlert error={list.error} onRetry={list.reload} />
          </div>
        ) : list.data!.items.length === 0 ? (
          <EmptyState title={t("noPackagesInTab")} />
        ) : (
          <>
            <ul className="divide-y divide-line">
              {list.data!.items.map((p) => (
                <li key={p.id}>
                  <Link
                    to={`/learner/packages/${p.id}`}
                    className="flex flex-col gap-2 px-5 py-4 transition hover:bg-primary-50/40 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <p className="code-text font-bold text-primary-700">{p.internal_code}</p>
                      <p className="text-sm text-muted">
                        {p.courier_name} • {t("thArrived")} {formatDateTime(p.arrived_at)}
                        {p.storage_location && (
                          <span className="ml-2 inline-flex items-center rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-700">
                            {t("thShelf")}: {p.storage_location.code}
                          </span>
                        )}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <StatusBadge status={p.status} learner />
                      {p.is_overdue && <OverdueFlag />}
                    </div>
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
