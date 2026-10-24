import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { packagesApi, type PackageQuery } from "../../api/endpoints";
import { PackageTable } from "../../components/PackageTable";
import { Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import type { TranslationDictionary } from "../../i18n/types";
import { useApi } from "../../lib/useApi";

interface TabDef {
  key: string;
  labelKey: keyof TranslationDictionary;
  query: PackageQuery;
  emptyKey: keyof TranslationDictionary;
}

const TABS: TabDef[] = [
  { key: "overdue", labelKey: "tabOverdue", query: { overdue: true }, emptyKey: "emptyOverdue" },
  { key: "unidentified", labelKey: "tabUnidentified", query: { status: ["UNIDENTIFIED"] }, emptyKey: "emptyUnidentified" },
  { key: "damaged", labelKey: "tabDamaged", query: { condition: "DAMAGED" }, emptyKey: "emptyDamaged" },
  { key: "investigation", labelKey: "tabInvestigation", query: { status: ["UNDER_INVESTIGATION"] }, emptyKey: "emptyInvestigation" },
  { key: "returns", labelKey: "tabReturns", query: { status: ["RETURN_REQUESTED"] }, emptyKey: "emptyReturns" },
];

export function ExceptionsPage() {
  const { t } = useLanguage();
  const [params, setParams] = useSearchParams();
  const tab = TABS.find((t) => t.key === params.get("tab")) ?? TABS[0];
  const [page, setPage] = useState(1);
  const list = useApi(() => packagesApi.list({ ...tab.query, page, page_size: 20 }), [tab.key, page]);

  return (
    <div>
      <PageHeader
        title={t("exceptionsTitle")}
        description={t("exceptionsDesc")}
      />
      <div className="mb-4 flex flex-wrap gap-1 rounded-xl border border-line bg-white p-1 sm:w-fit" role="tablist">
        {TABS.map((tabItem) => (
          <button
            key={tabItem.key}
            role="tab"
            aria-selected={tabItem.key === tab.key}
            className={`rounded-lg px-3.5 py-1.5 text-sm font-semibold transition ${
              tabItem.key === tab.key ? "bg-primary-50 text-primary-700 shadow-sm" : "text-muted hover:text-ink"
            }`}
            onClick={() => {
              setParams({ tab: tabItem.key });
              setPage(1);
            }}
          >
            {t(tabItem.labelKey)}
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
          <EmptyState title={t(tab.emptyKey)} />
        ) : (
          <>
            <PackageTable packages={list.data!.items} basePath="/ops/packages" />
            <Pagination page={page} pageSize={20} total={list.data!.total} onPage={setPage} />
          </>
        )}
      </Card>
    </div>
  );
}
