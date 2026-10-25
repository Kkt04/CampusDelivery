import { FormEvent, useState } from "react";
import { newIdempotencyKey } from "../../api/client";
import { pickupApi } from "../../api/endpoints";
import type { Package, PickupInput, PickupRecord } from "../../api/types";
import { Alert, Button, Card, ErrorAlert, Field, KeyValue, PageHeader } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatDateTime } from "../../lib/format";
import { useAction } from "../../lib/useApi";

export function PickupVerification() {
  const { t } = useLanguage();
  const [input, setInput] = useState<PickupInput>({ package_code: "", learner_institutional_id: "", code: "" });
  const [verified, setVerified] = useState<Package | null>(null);
  const [record, setRecord] = useState<PickupRecord | null>(null);
  const [idemKey, setIdemKey] = useState(newIdempotencyKey);

  // Supervisor Manual Override Modal
  const [showOverride, setShowOverride] = useState(false);
  const [overridePkgCode, setOverridePkgCode] = useState("");
  const [overrideLearnerId, setOverrideLearnerId] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [overridePending, setOverridePending] = useState(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);

  const clean = (): PickupInput => ({
    package_code: input.package_code.trim(),
    learner_institutional_id: input.learner_institutional_id.trim().toUpperCase(),
    code: input.code.replace(/\D/g, ""),
  });
  const verify = useAction(() => pickupApi.verify(clean()));
  const complete = useAction(() => pickupApi.complete(clean(), idemKey));

  function handleFormKeyDown(e: React.KeyboardEvent<HTMLFormElement>) {
    if (e.key === "Enter") {
      const target = e.target as HTMLInputElement;
      if (target.tagName === "BUTTON") return;

      if (!input.package_code || !input.learner_institutional_id || input.code.replace(/\D/g, "").length !== 6) {
        e.preventDefault();
        if (target.id === "pkg") {
          document.getElementById("lrn")?.focus();
        } else if (target.id === "lrn") {
          document.getElementById("code")?.focus();
        }
      }
    }
  }

  async function onVerify(e: FormEvent) {
    e.preventDefault();
    const result = await verify.run();
    if (result) setVerified(result.package);
  }

  async function onOverrideSubmit(e: FormEvent) {
    e.preventDefault();
    setOverrideError(null);
    if (overrideReason.trim().length < 5) {
      setOverrideError("Please provide an explicit reason of at least 5 characters.");
      return;
    }
    setOverridePending(true);
    try {
      const r = await pickupApi.override(
        {
          package_code: overridePkgCode.trim(),
          learner_institutional_id: overrideLearnerId.trim().toUpperCase(),
          reason: overrideReason.trim(),
        },
        idemKey
      );
      setRecord(r);
      setShowOverride(false);
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "message" in err ? String(err.message) : "Override failed.";
      setOverrideError(msg);
    } finally {
      setOverridePending(false);
    }
  }

  function reset() {
    setInput({ package_code: "", learner_institutional_id: "", code: "" });
    setVerified(null);
    setRecord(null);
    setIdemKey(newIdempotencyKey());
  }

  const set = (k: keyof PickupInput) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput({ ...input, [k]: e.target.value });
    setVerified(null);
  };

  if (record) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <PageHeader title={t("pickupHandedOver")} />
        <Alert tone="success" title={`${record.internal_code} ${t("pickupHandedOver")}`}>
          {t("pickupSuccessBanner")} ({formatDateTime(record.collected_at)})
          {record.storage_location_code && (
            <span className="block mt-1">
              {t("thShelf")}: <strong className="font-mono">{record.storage_location_code}</strong>
            </span>
          )}
          {record.is_override && (
            <div className="mt-3 rounded-lg bg-amber-50 border border-amber-200 p-2.5 text-xs text-amber-900">
              <span className="font-bold uppercase tracking-wider text-[10px] bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded mr-1.5">
                Identity Override Handover
              </span>
              <span>Reason: {record.override_reason}</span>
            </div>
          )}
        </Alert>
        <Button onClick={reset}>{t("pickupNextBtn")}</Button>
      </div>
    );
  }

  const error = verify.error ?? complete.error;
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader
        title={t("pickupVerifyTitle")}
        description={t("pickupVerifySubtitle")}
      />

      <form onSubmit={onVerify} onKeyDown={handleFormKeyDown} className="card space-y-4 p-5" noValidate>
        <ErrorAlert error={error} />
        <Field label="Package Code or Courier Tracking Barcode" htmlFor="pkg" hint="Scan the physical courier label barcode or internal code (e.g. 1Z..., PKG-...)">
          <input
            id="pkg"
            className="input code-text font-semibold uppercase"
            placeholder="Scan courier barcode or PKG-..."
            value={input.package_code}
            onChange={set("package_code")}
            autoComplete="off"
            required
          />
        </Field>
        <Field label={t("pickupStudentIdLabel")} htmlFor="lrn">
          <input
            id="lrn"
            className="input uppercase font-semibold"
            placeholder={t("pickupStudentIdPlaceholder")}
            value={input.learner_institutional_id}
            onChange={set("learner_institutional_id")}
            autoComplete="off"
            required
          />
        </Field>
        <Field label={t("pickupCodeLabel")} htmlFor="code" hint="6-digit single-use OTP code provided by student">
          <input
            id="code"
            className="input code-text text-xl tracking-[0.3em] font-bold text-center"
            inputMode="numeric"
            maxLength={6}
            placeholder="• • • • • •"
            value={input.code}
            onChange={set("code")}
            autoComplete="one-time-code"
            required
          />
        </Field>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
          <Button
            type="submit"
            variant={verified ? "secondary" : "primary"}
            pending={verify.pending}
            disabled={!input.package_code.trim() || !input.learner_institutional_id.trim() || input.code.replace(/\D/g, "").length !== 6}
          >
            {t("pickupVerifyBtn")}
          </Button>

          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setOverridePkgCode(input.package_code);
              setOverrideLearnerId(input.learner_institutional_id);
              setShowOverride(true);
            }}
            className="text-xs text-amber-700 hover:text-amber-800 hover:bg-amber-50"
          >
            ⚠️ Manual Override (Supervisor)
          </Button>
        </div>
      </form>

      {verified && (
        <Card title={t("pickupValidCardTitle")}>
          <KeyValue
            items={[
              [t("thRecipient"), `${verified.recipient?.full_name ?? verified.recipient_hint} (${verified.recipient?.institutional_id ?? "–"})`],
              [t("thPackage"), verified.internal_code],
              [t("thShelf"), verified.storage_location?.code ?? "–"],
              [t("thCourier"), verified.courier_name],
              ["Courier Tracking ID", verified.tracking_id ?? "–"],
            ]}
          />
          <p className="mt-4 text-sm text-muted">{t("pickupFetchNotice")}</p>
          <Button
            className="mt-4 w-full sm:w-auto"
            pending={complete.pending}
            onClick={async () => {
              const r = await complete.run();
              if (r) setRecord(r);
            }}
          >
            {t("pickupCompleteBtn")}
          </Button>
        </Card>
      )}

      {/* Supervisor Manual Override Modal */}
      {showOverride && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-line bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div>
                <h2 className="text-lg font-bold text-ink font-serif">Manual Identity Override</h2>
                <p className="text-xs text-muted">Authorized supervisor handover when code is lost or locked out</p>
              </div>
              <button
                type="button"
                onClick={() => setShowOverride(false)}
                className="rounded-lg p-1 text-muted hover:bg-surface-alt hover:text-ink transition-colors"
              >
                ✕
              </button>
            </div>

            {overrideError && <Alert tone="danger">{overrideError}</Alert>}

            <Alert tone="warn">
              You must physically verify the student's institutional photo ID before completing a manual handover. This action is permanently audited.
            </Alert>

            <form onSubmit={onOverrideSubmit} className="space-y-3.5">
              <Field label="Package Code or Tracking ID" htmlFor="ov_pkg">
                <input
                  id="ov_pkg"
                  className="input font-mono uppercase"
                  required
                  value={overridePkgCode}
                  onChange={(e) => setOverridePkgCode(e.target.value)}
                  placeholder="PKG-... or Courier AWB"
                />
              </Field>

              <Field label="Verified Student Institutional ID" htmlFor="ov_lrn">
                <input
                  id="ov_lrn"
                  className="input font-mono uppercase"
                  required
                  value={overrideLearnerId}
                  onChange={(e) => setOverrideLearnerId(e.target.value)}
                  placeholder="Student ID from physical card"
                />
              </Field>

              <Field label="Mandatory Reason for Override" htmlFor="ov_reason" hint="Must be at least 5 characters (e.g. Student phone battery died, physical ID verified)">
                <textarea
                  id="ov_reason"
                  className="input min-h-[70px] text-sm"
                  required
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Enter reason for manual override..."
                />
              </Field>

              <div className="flex gap-2 pt-2">
                <Button type="submit" variant="danger" pending={overridePending} className="flex-1">
                  Authorize & Handover
                </Button>
                <Button type="button" variant="ghost" onClick={() => setShowOverride(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
