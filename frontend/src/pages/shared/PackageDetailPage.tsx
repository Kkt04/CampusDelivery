import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { incidentsApi, packagesApi, storageApi } from "../../api/endpoints";
import type { Incident, IncidentComment, Package, PackageAction, PackageStatus, Role, UserBrief } from "../../api/types";
import { useUser } from "../../auth/AuthContext";
import { LearnerPicker } from "../../components/LearnerPicker";
import { LifecycleTrack } from "../../components/LifecycleTrack";
import { OverdueFlag, StatusBadge } from "../../components/StatusBadge";
import { Alert, Button, Card, ErrorAlert, Field, KeyValue, PageHeader, Spinner, TextLink } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatDateTime, sentenceCase } from "../../lib/format";
import { useAction, useApi } from "../../lib/useApi";

const BASE: Record<Role, string> = { LEARNER: "/learner/packages", SECURITY: "/security/packages", ADMIN: "/ops/packages" };
const STORABLE: PackageStatus[] = [
  "VERIFIED", "STORED", "READY_FOR_PICKUP", "PICKUP_REQUESTED", "UNIDENTIFIED", "DAMAGED",
  "UNDER_INVESTIGATION", "RETURN_REQUESTED",
];
const SIZE_RANK = { SMALL: 1, MEDIUM: 2, LARGE: 3 } as const;

export function PackageDetailPage() {
  const { t } = useLanguage();
  const user = useUser();
  const id = Number(useParams().id);
  const pkg = useApi(() => packagesApi.get(id), [id]);
  const history = useApi(() => packagesApi.history(id), [id]);
  const [flash, setFlash] = useState<string | null>(null);
  const isLearner = user.role === "LEARNER";

  if (pkg.loading && !pkg.data) return <Spinner label={t("loading")} />;
  if (pkg.error) {
    return (
      <div className="space-y-4">
        <ErrorAlert error={pkg.error} onRetry={pkg.error.status === 404 ? undefined : pkg.reload} />
        <TextLink to={BASE[user.role]}>{t("backToPackages")}</TextLink>
      </div>
    );
  }
  const p = pkg.data!;
  const onUpdated = (updated: Package, message: string) => {
    pkg.setData(updated);
    setFlash(message);
    void history.reload();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={p.internal_code}
        description={<span>{p.courier_name}{p.tracking_id ? `, ${t("regTrackingLabel")} ${p.tracking_id}` : ""}</span>}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={p.status} learner={isLearner} />
            {p.is_overdue && <OverdueFlag />}
          </div>
        }
      />
      {flash && <Alert tone="success">{flash}</Alert>}

      <Card title={t("progressTitle")}>
        <LifecycleTrack status={p.status} history={history.data ?? []} learner={isLearner} />
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <Card title={t("details")}>
          <KeyValue
            items={[
              [t("thRecipient"), p.recipient ? `${p.recipient.full_name} (${p.recipient.institutional_id})` : <span className="text-warn">{p.recipient_hint ?? t("unknownRecipientText")}</span>],
              [t("thCourier"), p.courier_name],
              [t("regTrackingLabel"), p.tracking_id ?? t("noTrackingId")],
              [t("regSizeLabel"), sentenceCase(p.size)],
              [t("thShelf"), p.storage_location?.code ?? (isLearner ? "–" : "–")],
              [t("thArrived"), formatDateTime(p.arrived_at)],
              [t("statusReadyForPickup"), formatDateTime(p.ready_at)],
              ...(p.closed_at ? [[t("statusCollected"), formatDateTime(p.closed_at)] as [string, string]] : []),
              ...(!isLearner
                ? ([
                    [t("roleSecurity"), p.received_by ? `${p.received_by.full_name} (${p.received_by.institutional_id})` : "–"],
                  ] as [string, string][])
                : []),
            ]}
          />
        </Card>

        <div className="space-y-6">
          {isLearner ? (
            <LearnerPanel pkg={p} onUpdated={onUpdated} />
          ) : (
            <>
              {!p.recipient && ["UNIDENTIFIED", "DAMAGED", "UNDER_INVESTIGATION"].includes(p.status) && (
                <IdentifyPanel pkg={p} onUpdated={onUpdated} />
              )}
              {STORABLE.includes(p.status) && <StoragePanel pkg={p} onUpdated={onUpdated} />}
              <ActionsPanel pkg={p} onUpdated={onUpdated} />
              {user.role === "SECURITY" && (
                <p className="text-sm">
                  <TextLink to={`/security/incidents?package=${p.id}`}>{t("reportIncidentForPkg")}</TextLink>
                </p>
              )}
            </>
          )}
        </div>
      </div>

      {!isLearner && (
        <Card title={t("pkgHistoryCard")} bodyClass="p-0">
          {history.loading ? (
            <div className="px-5 py-4"><Spinner /></div>
          ) : (
            <ol className="divide-y divide-line">
              {(history.data ?? []).slice().reverse().map((h, i) => (
                <li key={i} className="flex flex-col gap-1 px-5 py-3 text-sm sm:flex-row sm:items-start sm:gap-6">
                  <span className="w-36 shrink-0 text-muted">{formatDateTime(h.created_at)}</span>
                  <div>
                    <p className="font-semibold text-ink">{h.to_label}</p>
                    <p className="text-muted">{h.reason ?? ""}{h.changed_by ? `, by ${h.changed_by.full_name}` : ""}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}
    </div>
  );
}

function LearnerPanel({ pkg, onUpdated }: { pkg: Package; onUpdated: (p: Package, message: string) => void }) {
  const { t } = useLanguage();
  const canCollect = pkg.status === "READY_FOR_PICKUP" || pkg.status === "PICKUP_REQUESTED";
  const canReturn = ["STORED", "READY_FOR_PICKUP", "PICKUP_REQUESTED"].includes(pkg.status);
  const [description, setDescription] = useState("");
  const [sent, setSent] = useState(false);
  const [showNewReport, setShowNewReport] = useState(false);

  const incidents = useApi(() => incidentsApi.list({ package_id: pkg.id }), [pkg.id, sent]);
  const report = useAction(() => incidentsApi.create({ package_id: pkg.id, type: "LEARNER_REPORTED_ISSUE", description, escalate: false }));

  async function onReport(e: FormEvent) {
    e.preventDefault();
    if (await report.run()) {
      setSent(true);
      setDescription("");
      setShowNewReport(false);
      void incidents.reload();
    }
  }

  const existingIncidents = incidents.data?.items ?? [];

  return (
    <>
      <Card title={t("pkgCollectCard")}>
        {canCollect ? (
          <div className="space-y-3 text-sm">
            <p>
              {t("pkgCollectInstructions")}{" "}
              <strong className="code-text font-bold text-primary-700 bg-primary-50 px-2 py-0.5 rounded border border-primary-200">
                {pkg.storage_location?.code ?? "–"}
              </strong>
            </p>
            <Link
              to={`/learner/packages/${pkg.id}/pickup`}
              className="inline-flex rounded-lg bg-primary-700 px-4 py-2 font-semibold text-white shadow-sm hover:bg-primary-800 transition"
            >
              {pkg.status === "PICKUP_REQUESTED" ? t("pkgNewCodeBtn") : t("pkgGetCodeBtn")}
            </Link>
          </div>
        ) : (
          <p className="text-sm text-muted">
            {pkg.status === "COLLECTED" ? t("pkgCollectedNotice") : t("pkgPendingNotice")}
          </p>
        )}
      </Card>

      {canReturn && <ReturnPanel pkg={pkg} onUpdated={onUpdated} />}

      {pkg.status === "RETURN_REQUESTED" && (
        <Card title={t("statusReturnRequested")}>
          <p className="text-sm text-muted">{t("pkgReturnRequestedNotice")}</p>
        </Card>
      )}

      {/* Reported Incidents & Communication Thread */}
      {existingIncidents.map((inc) => (
        <LearnerIncidentItem key={inc.id} incident={inc} onReload={() => void incidents.reload()} />
      ))}

      {/* Report a Problem Form */}
      {existingIncidents.length === 0 || showNewReport ? (
        <Card title={t("pkgReportProblem")}>
          {sent ? (
            <Alert tone="success">{t("pkgReportSuccess")}</Alert>
          ) : (
            <form className="space-y-3" onSubmit={onReport}>
              <ErrorAlert error={report.error} />
              <Field label={t("pkgReportDescLabel")} htmlFor="issue" error={report.error?.fieldErrors.description}>
                <textarea
                  id="issue"
                  className="input min-h-24"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t("pkgReportDescPlaceholder")}
                />
              </Field>
              <div className="flex gap-2">
                <Button variant="secondary" type="submit" pending={report.pending} disabled={description.trim().length < 5}>
                  {t("pkgReportBtn")}
                </Button>
                {existingIncidents.length > 0 && (
                  <Button variant="ghost" type="button" onClick={() => setShowNewReport(false)}>
                    {t("cancel")}
                  </Button>
                )}
              </div>
            </form>
          )}
        </Card>
      ) : (
        <div className="text-center pt-1">
          <Button variant="ghost" className="text-xs py-1.5 px-3" onClick={() => setShowNewReport(true)}>
            + {t("pkgReportProblem")}
          </Button>
        </div>
      )}
    </>
  );
}

function LearnerIncidentItem({ incident: inc, onReload }: { incident: Incident; onReload: () => void }) {
  const { t } = useLanguage();
  const [replyText, setReplyText] = useState("");
  const replyAction = useAction(() => incidentsApi.addComment(inc.id, replyText));

  return (
    <Card title={`#${inc.id} ${sentenceCase(inc.type)}`}>
      <div className="space-y-4">
        {/* Status and timestamp */}
        <div className="flex items-center justify-between">
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
              inc.status === "OPEN"
                ? "bg-amber-50 text-amber-800 border-amber-200"
                : "bg-emerald-50 text-emerald-800 border-emerald-200"
            }`}
          >
            {inc.status === "OPEN" ? t("filterOpen") : t("filterResolved")}
          </span>
          <span className="text-xs text-muted">{formatDateTime(inc.created_at)}</span>
        </div>

        {/* Reported message */}
        <div className="rounded-lg bg-surface-alt p-3.5 border border-line">
          <p className="text-[11px] font-bold text-muted uppercase tracking-wider mb-1">
            {t("reportedIssueLabel")}
          </p>
          <p className="text-sm font-medium text-ink whitespace-pre-wrap leading-relaxed">{inc.description}</p>
        </div>

        {/* Communication Thread */}
        <div className="space-y-2.5">
          <h4 className="text-xs font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
            <span>💬</span> <span>{t("incidentConversationTitle")}</span>
          </h4>

          {inc.comments && inc.comments.length > 0 ? (
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {inc.comments.map((c: IncidentComment) => {
                const isAdmin = c.author_role === "ADMIN";
                return (
                  <div
                    key={c.id}
                    className={`rounded-xl p-3 text-xs border ${
                      isAdmin ? "bg-brand/5 border-brand/20 ml-4" : "bg-surface-alt border-line mr-4"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-ink">{c.author_name}</span>
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.2 rounded uppercase ${
                            isAdmin ? "bg-brand text-white" : "bg-neutral-200 text-neutral-700"
                          }`}
                        >
                          {isAdmin ? "Admin" : "You"}
                        </span>
                      </div>
                      <span className="text-[10px] text-muted">{formatDateTime(c.created_at)}</span>
                    </div>
                    <p className="text-sm text-text whitespace-pre-wrap leading-relaxed">{c.message}</p>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-muted italic bg-surface-alt rounded-lg p-3 border border-line">
              {t("noFollowUpMessages")}
            </p>
          )}

          {/* Follow-up input for active incident */}
          {inc.status === "OPEN" && (
            <div className="pt-2 space-y-2 border-t border-line">
              <ErrorAlert error={replyAction.error} />
              <textarea
                className="input min-h-16 text-sm"
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder={t("replyPlaceholder")}
                aria-label={t("replyPlaceholder")}
              />
              <div className="flex justify-end">
                <Button
                  className="text-xs py-1.5 px-3"
                  pending={replyAction.pending}
                  disabled={!replyText.trim()}
                  onClick={async () => {
                    const res = await replyAction.run();
                    if (res) {
                      setReplyText("");
                      onReload();
                    }
                  }}
                >
                  {t("sendReplyBtn")}
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Resolution note if resolved */}
        {inc.status === "RESOLVED" && (
          <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-950">
            <p className="font-bold text-sm">
              ✓ {t("resolvedByLabel")}: {inc.resolved_by?.full_name ?? "Admin"}
              {inc.resolved_at && ` • ${formatDateTime(inc.resolved_at)}`}
            </p>
            {inc.resolution_note && (
              <p className="mt-1.5 text-sm bg-white/80 rounded p-2 border border-emerald-100 text-text leading-relaxed">
                {inc.resolution_note}
              </p>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

function ReturnPanel({ pkg, onUpdated }: { pkg: Package; onUpdated: (p: Package, message: string) => void }) {
  const { t } = useLanguage();
  const [reason, setReason] = useState("");
  const request = useAction(() => packagesApi.requestReturn(pkg.id, reason.trim()));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const updated = await request.run();
    if (updated) onUpdated(updated, t("pkgReturnRequestedNotice"));
  }

  return (
    <Card title={t("returnToCourier")}>
      <form className="space-y-3" onSubmit={onSubmit}>
        <p className="text-sm text-muted">
          Ask Gate No. 2 to send this package back to {pkg.courier_name}.
        </p>
        <ErrorAlert error={request.error} />
        <Field label={t("returnReasonLabel")} htmlFor="return-reason">
          <textarea
            id="return-reason"
            className="input min-h-20"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t("returnReasonPlaceholder")}
          />
        </Field>
        <Button variant="danger" type="submit" pending={request.pending} disabled={reason.trim().length < 3}>
          {t("requestReturnBtn")}
        </Button>
      </form>
    </Card>
  );
}

function StoragePanel({ pkg, onUpdated }: { pkg: Package; onUpdated: (p: Package, m: string) => void }) {
  const { t } = useLanguage();
  const locations = useApi(() => storageApi.list(true), []);
  const [locationId, setLocationId] = useState<string>("auto");
  const canMarkReady = !!pkg.recipient && (pkg.status === "VERIFIED" || pkg.status === "STORED");
  const [markReady, setMarkReady] = useState(canMarkReady);
  const assign = useAction(() =>
    packagesApi.assignStorage(pkg.id, locationId === "auto" ? null : Number(locationId), markReady && canMarkReady)
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const updated = await assign.run();
    if (updated) {
      onUpdated(
        updated,
        `${t("regStoredAtShelf")} ${updated.storage_location?.code}${
          updated.status === "READY_FOR_PICKUP" ? " - " + t("regReadyNotification") : "."
        }`
      );
    }
  }

  return (
    <Card title={pkg.storage_location ? `${t("thShelf")}: ${pkg.storage_location.code}` : t("pkgAssignStorageTitle")}>
      <form className="space-y-3" onSubmit={onSubmit}>
        <ErrorAlert error={assign.error} />
        <Field label={pkg.storage_location ? t("movePackage") : t("thShelf")} htmlFor="location">
          <select id="location" className="input" value={locationId} onChange={(e) => setLocationId(e.target.value)}>
            <option value="auto">Auto</option>
            {(locations.data ?? []).map((l) => {
              const free = l.capacity - l.occupied_count;
              const fits = SIZE_RANK[pkg.size] <= SIZE_RANK[l.max_package_size];
              return (
                <option key={l.id} value={l.id} disabled={(free <= 0 || !fits) && l.id !== pkg.storage_location?.id}>
                  {l.code}, {free} free
                </option>
              );
            })}
          </select>
        </Field>
        {canMarkReady && (
          <label className="flex items-center gap-2 text-sm text-ink cursor-pointer">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              checked={markReady}
              onChange={(e) => setMarkReady(e.target.checked)}
            />
            {t("regReadyNotification")}
          </label>
        )}
        <Button type="submit" pending={assign.pending}>
          {pkg.storage_location ? t("movePackage") : t("pkgAssignStorageTitle")}
        </Button>
      </form>
    </Card>
  );
}

function IdentifyPanel({ pkg, onUpdated }: { pkg: Package; onUpdated: (p: Package, m: string) => void }) {
  const { t } = useLanguage();
  const [learner, setLearner] = useState<UserBrief | null>(null);
  const identify = useAction(() => packagesApi.identifyRecipient(pkg.id, learner!.institutional_id));

  return (
    <Card title={t("identifyRecipientTitle")}>
      <div className="space-y-3">
        <p className="text-sm text-muted">
          {t("identifyRecipientHelp")} <strong className="text-ink">{pkg.recipient_hint ?? "–"}</strong>
        </p>
        <ErrorAlert error={identify.error} />
        <LearnerPicker id="identify-learner" value={learner} onChange={setLearner} />
        <Button
          disabled={!learner}
          pending={identify.pending}
          onClick={async () => {
            const u = await identify.run();
            if (u) onUpdated(u, `${t("thRecipient")}: ${u.recipient?.full_name}`);
          }}
        >
          {t("setRecipientBtn")}
        </Button>
      </div>
    </Card>
  );
}

const REASON_REQUIRED: PackageStatus[] = ["UNDER_INVESTIGATION", "RETURN_REQUESTED", "LOST", "DAMAGED"];

function ActionsPanel({ pkg, onUpdated }: { pkg: Package; onUpdated: (p: Package, m: string) => void }) {
  const { t } = useLanguage();
  const actions = pkg.available_actions.filter((a) => !a.dedicated);
  const [chosen, setChosen] = useState<PackageAction | null>(null);
  const [reason, setReason] = useState("");
  const apply = useAction(() => packagesApi.transition(pkg.id, chosen!.target_status, reason.trim() || undefined));
  if (actions.length === 0) return null;
  const needsReason = chosen ? REASON_REQUIRED.includes(chosen.target_status) : false;

  return (
    <Card title={t("pkgActionsCard")}>
      {!chosen ? (
        <div className="flex flex-wrap gap-2">
          {actions.map((a) => (
            <Button
              key={`${a.action}-${a.target_status}`}
              variant={["LOST", "RETURN_REQUESTED"].includes(a.target_status) ? "danger" : "secondary"}
              onClick={() => {
                setChosen(a);
                setReason("");
                apply.setError(null);
              }}
            >
              {a.label}
            </Button>
          ))}
        </div>
      ) : (
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            const updated = await apply.run();
            if (updated) {
              onUpdated(updated, `${chosen.label}: done.`);
              setChosen(null);
            }
          }}
        >
          <p className="text-sm font-semibold text-ink">{chosen.label}</p>
          <ErrorAlert error={apply.error} />
          <Field label={needsReason ? "Reason (required)" : "Note (optional)"} htmlFor="reason">
            <textarea id="reason" className="input min-h-20" value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
          <div className="flex gap-2">
            <Button type="submit" pending={apply.pending} disabled={needsReason && reason.trim().length === 0}>
              {t("confirm")}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setChosen(null)}>
              {t("cancel")}
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}
