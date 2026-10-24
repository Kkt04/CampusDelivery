import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { packagesApi, pickupApi } from "../../api/endpoints";
import type { PickupCode } from "../../api/types";
import { useUser } from "../../auth/AuthContext";
import { Alert, Button, ErrorAlert, PageHeader, Spinner, TextLink } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { useAction, useApi } from "../../lib/useApi";

function useCountdown(expiresAt: string | null) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!expiresAt) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [expiresAt]);
  return expiresAt ? Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000)) : 0;
}

export function PickupCodePage() {
  const { t } = useLanguage();
  const user = useUser();
  const id = Number(useParams().id);
  const pkg = useApi(() => packagesApi.get(id), [id]);
  const [issued, setIssued] = useState<PickupCode | null>(null);
  const [ttl, setTtl] = useState(0);
  const requestCode = useAction(() => pickupApi.requestCode(id));
  const secondsLeft = useCountdown(issued?.expires_at ?? null);

  async function onRequest() {
    const result = await requestCode.run();
    if (result) {
      setIssued(result);
      setTtl(Math.max(1, Math.round((new Date(result.expires_at).getTime() - Date.now()) / 1000)));
      void pkg.reload();
    }
  }

  if (pkg.loading && !pkg.data) return <Spinner label={t("loading")} />;
  if (pkg.error) return <ErrorAlert error={pkg.error} />;
  const p = pkg.data!;
  const expired = issued !== null && secondsLeft === 0;
  const eligible = p.status === "READY_FOR_PICKUP" || p.status === "PICKUP_REQUESTED";

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader
        title={t("pickupCodePageTitle")}
        description={`${t("thPackage")} ${p.internal_code} (${p.courier_name})`}
      />

      {!eligible ? (
        <Alert tone="info" title={t("pkgPendingNotice")}>
          {p.status === "COLLECTED" ? t("pkgCollectedNotice") : t("pkgPendingNotice")}{" "}
          <TextLink to={`/learner/packages/${p.id}`}>{t("pickupCodeBack")}</TextLink>
        </Alert>
      ) : !issued || expired ? (
        <div className="card space-y-4 p-6">
          {expired && (
            <Alert tone="warn" title={t("codeExpiredTitle")}>
              {t("codeExpiredDesc")}
            </Alert>
          )}
          <p className="text-sm text-muted">
            {t("codeGatePrompt")}
          </p>
          <ErrorAlert error={requestCode.error} />
          <Button onClick={onRequest} pending={requestCode.pending}>
            {expired || p.status === "PICKUP_REQUESTED" ? t("pkgNewCodeBtn") : t("getMyCode")}
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="ticket px-8 py-8 text-center bg-white shadow-ticket rounded-2xl border border-primary-200">
            <p className="text-sm font-medium text-primary-800">{t("pickupCodeInstructions")}</p>
            <p
              className="code-text mt-4 text-5xl font-black tracking-[0.2em] text-primary-950 sm:text-6xl"
              aria-label={`Pickup code ${issued.code.split("").join(" ")}`}
            >
              {issued.code.slice(0, 3)}
              <span className="mx-2 text-primary-300">–</span>
              {issued.code.slice(3)}
            </p>
            <div className="mx-auto mt-6 border-t-2 border-dashed border-primary-100 pt-5 text-sm">
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <p className="text-xs text-muted">{t("thPackage")}</p>
                  <p className="code-text font-bold text-ink">{issued.internal_code}</p>
                </div>
                <div>
                  <p className="text-xs text-muted">{t("thShelf")}</p>
                  <p className="code-text font-bold text-primary-700">{p.storage_location?.code ?? "–"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted">{t("pickupStudentIdLabel")}</p>
                  <p className="code-text font-bold text-ink">{user.institutional_id}</p>
                </div>
              </div>
            </div>
            <div className="mt-6">
              <div className="h-2 overflow-hidden rounded-full bg-primary-100" aria-hidden>
                <div
                  className="h-full bg-primary-600 transition-[width] duration-1000 ease-linear"
                  style={{ width: `${(secondsLeft / ttl) * 100}%` }}
                />
              </div>
              <p className="mt-2 text-sm font-semibold text-primary-900" role="timer" aria-live="off">
                {t("codeValidFor")} {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, "0")}
              </p>
            </div>
          </div>
          <p className="text-center text-xs text-muted">
            {t("codeNoticeOnce")}
          </p>
        </div>
      )}
    </div>
  );
}
