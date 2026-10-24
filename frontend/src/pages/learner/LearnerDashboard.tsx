import { Link } from "react-router-dom";
import { notificationsApi, packagesApi } from "../../api/endpoints";
import type { Package } from "../../api/types";
import { useUser } from "../../auth/AuthContext";
import { OverdueFlag, StatusBadge } from "../../components/StatusBadge";
import { Card, EmptyState, ErrorAlert, PageHeader, Spinner, TextLink } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatDateTime, timeAgo } from "../../lib/format";
import { useApi } from "../../lib/useApi";

export function LearnerDashboard() {
  const user = useUser();
  const { t } = useLanguage();
  const ready = useApi(() => packagesApi.list({ status: ["READY_FOR_PICKUP", "PICKUP_REQUESTED"], page_size: 10 }), []);
  const onTheWay = useApi(
    () =>
      packagesApi.list({
        status: ["RECEIVED", "VERIFIED", "STORED", "DAMAGED", "UNDER_INVESTIGATION", "RETURN_REQUESTED"],
        page_size: 10,
      }),
    []
  );
  const notes = useApi(() => notificationsApi.list(1), []);
  const returns = useApi(() => packagesApi.list({ status: ["RETURN_REQUESTED"], page_size: 5 }), []);

  return (
    <div className="space-y-8">
      <PageHeader title={`${t("roleLearner")}: ${user.full_name}`} description={t("brandSubtitle")} />

      {onTheWay.data && onTheWay.data.items.length > 0 && (
        <div className="rounded-xl border border-primary-200 bg-primary-50/70 p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📦</span>
            <div>
              <p className="font-semibold text-primary-950">
                {onTheWay.data.items.length} {t("thPackage")} Gate No. 2!
              </p>
              <p className="text-sm text-primary-800">
                {t("pkgCollectInstructions")} Gate No. 2
              </p>
            </div>
          </div>
        </div>
      )}

      <section>
        <h2 className="mb-3 text-lg font-bold text-ink">{t("readyToCollectTitle")}</h2>
        {ready.loading ? (
          <Spinner label={t("loading")} />
        ) : ready.error ? (
          <ErrorAlert error={ready.error} onRetry={ready.reload} />
        ) : ready.data!.items.length === 0 ? (
          <div className="card">
            <EmptyState title={t("noParcelsReady")} />
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {ready.data!.items.map((p) => (
              <ReadyCard key={p.id} pkg={p} />
            ))}
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={t("tabIncoming")} bodyClass="p-0">
          {onTheWay.loading ? (
            <div className="px-5 py-4"><Spinner /></div>
          ) : onTheWay.error ? (
            <div className="p-5"><ErrorAlert error={onTheWay.error} /></div>
          ) : onTheWay.data!.items.length === 0 ? (
            <p className="px-5 py-6 text-sm text-muted">{t("noPackagesInTab")}</p>
          ) : (
            <ul className="divide-y divide-line">
              {onTheWay.data!.items.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                  <Link to={`/learner/packages/${p.id}`} className="min-w-0">
                    <p className="code-text font-bold text-primary-700">{p.internal_code}</p>
                    <p className="text-muted">
                      {p.courier_name} • {t("thArrived")} {formatDateTime(p.arrived_at)}
                    </p>
                  </Link>
                  <StatusBadge status={p.status} learner />
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card
          title={t("notifTitle")}
          actions={<TextLink to="/notifications">{t("viewAll")}</TextLink>}
          bodyClass="p-0"
        >
          {notes.loading ? (
            <div className="px-5 py-4"><Spinner /></div>
          ) : notes.error ? (
            <div className="p-5"><ErrorAlert error={notes.error} /></div>
          ) : notes.data!.items.length === 0 ? (
            <p className="px-5 py-6 text-sm text-muted">{t("notifEmpty")}</p>
          ) : (
            <ul className="divide-y divide-line">
              {notes.data!.items.slice(0, 4).map((n) => (
                <li key={n.id} className="px-5 py-3 text-sm">
                  <p className="font-semibold text-ink">
                    {n.title} <span className="font-normal text-muted">{timeAgo(n.created_at)}</span>
                  </p>
                  <p className="text-muted">{n.message}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title={t("returnPageTitle")}
          actions={<TextLink to="/learner/returns">{t("initiateParcelReturn")}</TextLink>}
        >
          <div className="space-y-3 text-sm">
            <p className="text-muted">
              {t("returnPageSubtitle")}
            </p>
            {returns.data && returns.data.items.length > 0 ? (
              <div className="mt-2 space-y-2">
                <p className="font-semibold text-primary-900">{t("activeReturnRequests")}</p>
                <ul className="divide-y divide-line rounded-lg border border-line bg-surface-alt/50">
                  {returns.data.items.map((r) => (
                    <li key={r.id} className="flex items-center justify-between p-2.5 text-xs">
                      <div>
                        <Link to={`/learner/packages/${r.id}`} className="font-bold text-primary-700 hover:underline">
                          {r.internal_code}
                        </Link>{" "}
                        <span className="text-muted">({r.courier_name})</span>
                        <p className="text-ink">{r.notes ?? t("statusReturnRequested")}</p>
                      </div>
                      <StatusBadge status={r.status} learner />
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <Link
                to="/learner/returns"
                className="inline-flex items-center gap-1.5 rounded-lg border border-primary-200 bg-primary-50 px-3 py-1.5 text-xs font-semibold text-primary-800 hover:bg-primary-100 transition-all"
              >
                + {t("initiateParcelReturn")}
              </Link>
            )}
          </div>
        </Card>

        <Card
          title={t("pickupHistoryTitle")}
          actions={<TextLink to="/learner/history">{t("viewAll")}</TextLink>}
        >
          <p className="text-sm text-muted">
            {t("pickupHistorySubtitle")}
          </p>
          <div className="mt-4">
            <Link
              to="/learner/history"
              className="inline-flex items-center gap-1.5 rounded-lg border border-primary-200 bg-primary-50 px-3 py-1.5 text-xs font-semibold text-primary-800 hover:bg-primary-100 transition-all"
            >
              {t("viewPastPickups")}
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}

function ReadyCard({ pkg }: { pkg: Package }) {
  const { t } = useLanguage();
  return (
    <div className="card flex flex-col justify-between gap-4 p-5 border-primary-200 shadow-sm hover:border-primary-400 transition">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={pkg.status} learner />
          {pkg.is_overdue && <OverdueFlag />}
        </div>
        <p className="code-text mt-3 text-lg font-bold text-ink">{pkg.internal_code}</p>
        <p className="text-sm text-muted">
          {pkg.courier_name} • {t("thShelf")}: <strong className="text-primary-800 font-bold bg-primary-50 px-1.5 py-0.5 rounded border border-primary-200">{pkg.storage_location?.code ?? "–"}</strong>
        </p>
        {pkg.is_overdue && <p className="mt-2 text-xs font-semibold text-red-600">{t("overdue")}</p>}
      </div>
      <div className="flex items-center gap-3">
        <Link
          to={`/learner/packages/${pkg.id}/pickup`}
          className="rounded-lg bg-primary-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-800 transition"
        >
          {t("pkgGetCodeBtn")}
        </Link>
        <Link
          to={`/learner/packages/${pkg.id}`}
          className="rounded-lg px-3.5 py-2 text-sm font-semibold text-primary-800 hover:bg-primary-50 transition"
        >
          {t("details")}
        </Link>
      </div>
    </div>
  );
}
