import { useState } from "react";
import { notificationsApi } from "../../api/endpoints";
import { useUser } from "../../auth/AuthContext";
import { Button, Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner, TextLink } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { timeAgo } from "../../lib/format";
import { useApi } from "../../lib/useApi";

export function NotificationsPage() {
  const { t } = useLanguage();
  const user = useUser();
  const [page, setPage] = useState(1);
  const list = useApi(() => notificationsApi.list(page), [page]);

  async function markAll() {
    await notificationsApi.markAllRead();
    void list.reload();
  }
  async function markOne(id: number) {
    await notificationsApi.markRead(id);
    void list.reload();
  }

  return (
    <div>
      <PageHeader
        title={t("notifTitle")}
        description={t("notifSubtitle")}
        actions={
          list.data && list.data.items.some((n) => !n.read_at) ? (
            <Button variant="secondary" onClick={markAll}>
              {t("notifMarkAllRead")}
            </Button>
          ) : undefined
        }
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
          <EmptyState title={t("notifEmpty")} />
        ) : (
          <>
            <ul className="divide-y divide-line">
              {list.data!.items.map((n) => (
                <li key={n.id} className={`flex gap-4 px-5 py-4 ${n.read_at ? "" : "bg-primary-50/50"}`}>
                  <span
                    className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${n.read_at ? "bg-transparent" : "bg-primary-600"}`}
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="font-semibold text-ink">{n.title}</p>
                      <span className="text-xs text-muted">{timeAgo(n.created_at)}</span>
                    </div>
                    <p className="mt-0.5 text-sm text-muted">{n.message}</p>
                    <div className="mt-2 flex gap-4 text-sm">
                      {n.package_id && user.role === "LEARNER" && (
                        <TextLink to={`/learner/packages/${n.package_id}`}>{t("details")}</TextLink>
                      )}
                      {!n.read_at && (
                        <button
                          className="font-semibold text-primary-700 hover:text-primary-800 hover:underline"
                          onClick={() => markOne(n.id)}
                        >
                          {t("notifMarkAllRead")}
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
            <Pagination page={page} pageSize={list.data!.page_size} total={list.data!.total} onPage={setPage} />
          </>
        )}
      </Card>
    </div>
  );
}
