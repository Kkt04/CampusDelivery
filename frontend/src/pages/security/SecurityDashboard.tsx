import { Link } from "react-router-dom";
import { packagesApi, reportsApi } from "../../api/endpoints";
import type { PackageStatus } from "../../api/types";
import { CountStrip } from "../../components/CountStrip";
import { PackageTable } from "../../components/PackageTable";
import { Card, EmptyState, ErrorAlert, PageHeader, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { useApi } from "../../lib/useApi";

function Queue({ title, statuses, empty }: { title: string; statuses: PackageStatus[]; empty: string }) {
  const list = useApi(() => packagesApi.list({ status: statuses, page_size: 5 }), []);
  return (
    <Card title={`${title}${list.data ? ` (${list.data.total})` : ""}`} bodyClass="p-0">
      {list.loading ? (
        <div className="px-5 py-4"><Spinner /></div>
      ) : list.error ? (
        <div className="p-5"><ErrorAlert error={list.error} /></div>
      ) : list.data!.items.length === 0 ? (
        <EmptyState title={empty} />
      ) : (
        <PackageTable packages={list.data!.items} basePath="/security/packages" />
      )}
    </Card>
  );
}

export function SecurityDashboard() {
  const { t } = useLanguage();
  const stats = useApi(() => reportsApi.dashboard(), []);
  const s = stats.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("gateDashboardTitle")}
        description={t("gateDashboardSubtitle")}
        actions={
          <div className="flex items-center gap-3">
            <Link
              to="/security/register"
              className="rounded-lg bg-brand px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-strong transition active:scale-95"
            >
              + {t("navRegisterPackage")}
            </Link>
            <Link
              to="/security/pickup"
              className="rounded-lg border border-line bg-white px-3.5 py-2 text-sm font-semibold text-ink shadow-sm hover:bg-primary-50 hover:border-primary-300 transition active:scale-95"
            >
              {t("navPickupHandover")}
            </Link>
          </div>
        }
      />
      {stats.error ? (
        <ErrorAlert error={stats.error} onRetry={stats.reload} />
      ) : !s ? (
        <Spinner label={t("loading")} />
      ) : (
        <CountStrip
          items={[
            { label: t("statReceivedToday"), value: s.received_today },
            { label: t("statCollectedToday"), value: s.collected_today },
            { label: t("statInCustody"), value: s.in_custody, to: "/security/packages" },
            { label: t("statAwaitingStorage"), value: s.by_status.VERIFIED, tone: "brand" },
            { label: t("statUnidentified"), value: s.by_status.UNIDENTIFIED, tone: "warn" },
            { label: t("statHeldDamaged"), value: s.by_status.DAMAGED, tone: "danger" },
          ]}
        />
      )}
      <Queue
        title={t("queueWaitingShelf")}
        statuses={["VERIFIED"]}
        empty={t("queueWaitingShelfEmpty")}
      />
      <Queue
        title={t("queueNeedsReview")}
        statuses={["UNIDENTIFIED", "DAMAGED", "UNDER_INVESTIGATION"]}
        empty={t("queueNeedsReviewEmpty")}
      />
      <Queue
        title={t("queueStoredNotReady")}
        statuses={["STORED"]}
        empty={t("queueStoredNotReadyEmpty")}
      />
    </div>
  );
}
