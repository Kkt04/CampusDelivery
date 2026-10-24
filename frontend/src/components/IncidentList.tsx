import { useState } from "react";
import { incidentsApi } from "../api/endpoints";
import type { Incident } from "../api/types";
import { useLanguage } from "../i18n/LanguageContext";
import { formatDateTime, sentenceCase } from "../lib/format";
import { useAction, useApi } from "../lib/useApi";
import { Button, Card, EmptyState, ErrorAlert, Pagination, Spinner, TextLink } from "./ui";

export function IncidentList({ canResolve, packageBase = "/security/packages" }: { canResolve: boolean; packageBase?: string }) {
  const { t } = useLanguage();
  const [status, setStatus] = useState<"OPEN" | "RESOLVED" | "">("OPEN");
  const [page, setPage] = useState(1);
  const list = useApi(() => incidentsApi.list({ status: status || undefined, page }), [status, page]);

  return (
    <Card
      title={t("recentIncidentsCard")}
      bodyClass="p-0"
      actions={
        <select
          aria-label="Filter incidents"
          className="input w-auto py-1"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as typeof status);
            setPage(1);
          }}
        >
          <option value="OPEN">{t("filterOpen")}</option>
          <option value="RESOLVED">{t("filterResolved")}</option>
          <option value="">{t("filterAll")}</option>
        </select>
      }
    >
      {list.loading && !list.data ? (
        <div className="px-5 py-6"><Spinner label={t("loading")} /></div>
      ) : list.error ? (
        <div className="p-5"><ErrorAlert error={list.error} onRetry={list.reload} /></div>
      ) : list.data!.items.length === 0 ? (
        <EmptyState title={status === "OPEN" ? t("noOpenIncidents") : t("noData")} />
      ) : (
        <>
          <ul className="divide-y divide-line">
            {list.data!.items.map((i) => (
              <IncidentRow key={i.id} incident={i} canResolve={canResolve} packageBase={packageBase} onChanged={list.reload} />
            ))}
          </ul>
          <Pagination page={page} pageSize={list.data!.page_size} total={list.data!.total} onPage={setPage} />
        </>
      )}
    </Card>
  );
}

function IncidentRow({
  incident: i,
  canResolve,
  packageBase,
  onChanged,
}: {
  incident: Incident;
  canResolve: boolean;
  packageBase: string;
  onChanged: () => void;
}) {
  const { t } = useLanguage();
  const [note, setNote] = useState("");
  const [open, setOpen] = useState(false);
  const resolve = useAction(() => incidentsApi.resolve(i.id, note));

  return (
    <li className="px-5 py-4 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-semibold text-ink">#{i.id} {sentenceCase(i.type)}</p>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
          i.status === "OPEN" ? "bg-amber-50 text-amber-800 border border-amber-200" : "bg-emerald-50 text-emerald-800 border border-emerald-200"
        }`}>
          {i.status === "OPEN" ? t("filterOpen") : t("filterResolved")}
        </span>
      </div>
      <p className="mt-1 text-ink">{i.description}</p>
      <p className="mt-1 text-xs text-muted">
        {i.reported_by.full_name}, {formatDateTime(i.created_at)}
        {i.package_id && <> • <TextLink to={`${packageBase}/${i.package_id}`}>{i.package_code}</TextLink></>}
      </p>
      {i.status === "RESOLVED" && i.resolution_note && (
        <p className="mt-2 rounded-lg bg-surface-alt border border-line px-3 py-2 text-xs text-ink">
          {t("resolutionNoteLabel")}: {i.resolution_note} ({i.resolved_by?.full_name})
        </p>
      )}
      {canResolve && i.status === "OPEN" && (
        open ? (
          <div className="mt-3 space-y-2">
            <ErrorAlert error={resolve.error} />
            <textarea
              aria-label={t("resolutionNoteLabel")}
              className="input min-h-16"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t("resolutionPlaceholder")}
            />
            <div className="flex gap-2">
              <Button pending={resolve.pending} disabled={note.trim().length < 3} onClick={async () => { if (await resolve.run()) onChanged(); }}>
                {t("markResolvedBtn")}
              </Button>
              <Button variant="ghost" onClick={() => setOpen(false)}>{t("cancel")}</Button>
            </div>
          </div>
        ) : (
          <Button variant="secondary" className="mt-3" onClick={() => setOpen(true)}>
            {t("resolveBtn")}
          </Button>
        )
      )}
    </li>
  );
}
