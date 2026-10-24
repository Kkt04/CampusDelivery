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
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [commentText, setCommentText] = useState("");

  const resolve = useAction(() => incidentsApi.resolve(i.id, note));
  const commentAction = useAction(() => incidentsApi.addComment(i.id, commentText));

  return (
    <li className="px-5 py-4 text-sm transition-colors hover:bg-surface-alt/40">
      {/* Closed State Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-serif font-bold text-base text-ink tracking-tight">
              #{i.id} {sentenceCase(i.type)}
            </p>
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                i.status === "OPEN"
                  ? "bg-amber-50 text-amber-800 border-amber-200"
                  : "bg-emerald-50 text-emerald-800 border-emerald-200"
              }`}
            >
              {i.status === "OPEN" ? t("filterOpen") : t("filterResolved")}
            </span>
            {i.comments && i.comments.length > 0 && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-brand/10 text-brand border border-brand/20">
                💬 {i.comments.length}
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-muted">
            <span className="font-semibold text-text">{i.reported_by.full_name}</span>,{" "}
            {formatDateTime(i.created_at)}
            {i.package_id && (
              <>
                {" "}for{" "}
                <TextLink to={`${packageBase}/${i.package_id}`}>
                  {i.package_code ?? `PKG-${i.package_id}`}
                </TextLink>
              </>
            )}
          </p>
        </div>

        {/* Action Button: Open / Close */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant={open ? "ghost" : "secondary"}
            onClick={() => setOpen(!open)}
            className="text-xs py-1.5 px-3 shadow-2xs"
          >
            {open ? t("closeIncidentBtn") : t("openIncidentBtn")}
          </Button>
        </div>
      </div>

      {/* Expanded Interactive Communication & Resolution Box */}
      {open && (
        <div className="mt-4 pt-4 border-t border-line space-y-4 animate-in fade-in duration-200">
          {/* 1. User Reported Incident Box */}
          <div className="rounded-xl border border-line bg-surface-alt/70 p-4">
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand/10 text-brand font-bold text-xs">
                  👤
                </span>
                <span className="text-xs font-semibold text-ink">
                  {t("reportedByNotice")}:{" "}
                  <strong className="text-brand font-bold">{i.reported_by.full_name}</strong>{" "}
                  <span className="text-muted">({i.reported_by.institutional_id})</span>
                </span>
              </div>
              <span className="text-[11px] text-muted">{formatDateTime(i.created_at)}</span>
            </div>
            <div className="rounded-lg bg-white p-3.5 border border-line shadow-2xs">
              <p className="text-[11px] font-bold text-muted uppercase tracking-wider mb-1">
                {t("reportedIssueLabel")}
              </p>
              <p className="text-sm font-medium text-ink whitespace-pre-wrap leading-relaxed">
                {i.description}
              </p>
            </div>
          </div>

          {/* 2. Communication & Follow-up Messages Thread */}
          <div className="rounded-xl border border-line bg-white p-4 space-y-3 shadow-2xs">
            <div className="flex items-center justify-between border-b border-line pb-2.5">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
                <span>💬</span>
                <span>{t("incidentConversationTitle")}</span>
              </h4>
              <span className="text-xs font-semibold text-muted">
                {(i.comments?.length || 0)}{" "}
                {(i.comments?.length || 0) === 1 ? "message" : "messages"}
              </span>
            </div>

            {i.comments && i.comments.length > 0 ? (
              <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                {i.comments.map((c) => {
                  const isAdmin = c.author_role === "ADMIN";
                  return (
                    <div
                      key={c.id}
                      className={`rounded-xl p-3 text-xs border ${
                        isAdmin
                          ? "bg-brand/5 border-brand/20 ml-6"
                          : "bg-surface-alt border-line mr-6"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-ink">{c.author_name}</span>
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                              isAdmin ? "bg-brand text-white" : "bg-neutral-200 text-neutral-700"
                            }`}
                          >
                            {isAdmin ? "Admin" : c.author_role}
                          </span>
                        </div>
                        <span className="text-[10px] text-muted">{formatDateTime(c.created_at)}</span>
                      </div>
                      <p className="text-sm text-text font-normal whitespace-pre-wrap leading-relaxed">
                        {c.message}
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-muted italic bg-surface-alt rounded-lg p-3 border border-line">
                {t("noFollowUpMessages")}
              </p>
            )}

            {/* Follow-up / Comment Input */}
            <div className="pt-2 space-y-2">
              <ErrorAlert error={commentAction.error} />
              <textarea
                className="input min-h-18 text-sm"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder={t("replyPlaceholder")}
                aria-label={t("replyPlaceholder")}
              />
              <div className="flex justify-end">
                <Button
                  className="text-xs py-1.5 px-3"
                  pending={commentAction.pending}
                  disabled={!commentText.trim()}
                  onClick={async () => {
                    const updated = await commentAction.run();
                    if (updated) {
                      setCommentText("");
                      onChanged();
                    }
                  }}
                >
                  {t("sendReplyBtn")}
                </Button>
              </div>
            </div>
          </div>

          {/* 3. Resolution Box */}
          <div className="rounded-xl border border-line bg-surface-alt p-4 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
              <span>🛡️</span>
              <span>{t("resolveIncidentBoxTitle")}</span>
            </h4>

            {i.status === "RESOLVED" ? (
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3.5 text-xs text-emerald-950">
                <p className="font-bold text-sm">
                  ✓ {t("resolvedByLabel")}: {i.resolved_by?.full_name ?? "Admin"} ({i.resolved_by?.institutional_id ?? "–"})
                  {i.resolved_at && ` • ${formatDateTime(i.resolved_at)}`}
                </p>
                {i.resolution_note && (
                  <p className="mt-2 text-sm bg-white/80 rounded-md p-2.5 border border-emerald-100 text-text leading-relaxed">
                    {i.resolution_note}
                  </p>
                )}
              </div>
            ) : canResolve ? (
              <div className="space-y-2.5">
                <ErrorAlert error={resolve.error} />
                <textarea
                  aria-label={t("resolutionNoteLabel")}
                  className="input min-h-16 text-sm"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder={t("resolutionPlaceholder")}
                />
                <div className="flex justify-end">
                  <Button
                    pending={resolve.pending}
                    disabled={note.trim().length < 3}
                    onClick={async () => {
                      if (await resolve.run()) onChanged();
                    }}
                  >
                    {t("markResolvedBtn")}
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted italic">
                Only operations admins can resolve this incident.
              </p>
            )}
          </div>
        </div>
      )}
    </li>
  );
}
