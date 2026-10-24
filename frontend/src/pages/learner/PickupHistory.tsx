import { useState } from "react";
import { pickupApi } from "../../api/endpoints";
import { Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner, TextLink } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatDateTime } from "../../lib/format";
import { useApi } from "../../lib/useApi";

export function PickupHistory() {
  const { t } = useLanguage();
  const [page, setPage] = useState(1);
  const list = useApi(() => pickupApi.history(page), [page]);

  return (
    <div>
      <PageHeader
        title={t("pickupHistoryTitle")}
        description={t("pickupHistorySubtitle")}
      />
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
          <EmptyState title={t("noData")} />
        ) : (
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>{t("thPackage")}</th>
                  <th>{t("thCourier")}</th>
                  <th>{t("thShelf")}</th>
                  <th>{t("pickupHandedOver")}</th>
                </tr>
              </thead>
              <tbody>
                {list.data!.items.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <TextLink to={`/learner/packages/${r.package_id}`}>
                        <span className="code-text font-bold text-primary-700">{r.internal_code}</span>
                      </TextLink>
                    </td>
                    <td>{r.courier_name}</td>
                    <td className="code-text font-semibold text-primary-800">{r.storage_location_code ?? "–"}</td>
                    <td className="whitespace-nowrap">{formatDateTime(r.collected_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} pageSize={list.data!.page_size} total={list.data!.total} onPage={setPage} />
          </div>
        )}
      </Card>
    </div>
  );
}
