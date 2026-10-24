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

  const clean = (): PickupInput => ({
    package_code: input.package_code.trim().toUpperCase(),
    learner_institutional_id: input.learner_institutional_id.trim().toUpperCase(),
    code: input.code.replace(/\D/g, ""),
  });
  const verify = useAction(() => pickupApi.verify(clean()));
  const complete = useAction(() => pickupApi.complete(clean(), idemKey));

  async function onVerify(e: FormEvent) {
    e.preventDefault();
    const result = await verify.run();
    if (result) setVerified(result.package);
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
      <form onSubmit={onVerify} className="card space-y-4 p-5" noValidate>
        <ErrorAlert error={error} />
        <Field label={t("pickupPkgCodeLabel")} htmlFor="pkg" hint={t("pickupPkgCodeHint")}>
          <input
            id="pkg"
            className="input code-text uppercase font-semibold"
            placeholder="PKG-..."
            value={input.package_code}
            onChange={set("package_code")}
            autoComplete="off"
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
          />
        </Field>
        <Field label={t("pickupCodeLabel")} htmlFor="code">
          <input
            id="code"
            className="input code-text text-lg tracking-[0.3em] font-bold"
            inputMode="numeric"
            maxLength={7}
            placeholder="••••••"
            value={input.code}
            onChange={set("code")}
            autoComplete="one-time-code"
          />
        </Field>
        <Button
          type="submit"
          variant={verified ? "secondary" : "primary"}
          pending={verify.pending}
          disabled={!input.package_code || !input.learner_institutional_id || input.code.replace(/\D/g, "").length !== 6}
        >
          {t("pickupVerifyBtn")}
        </Button>
      </form>

      {verified && (
        <Card title={t("pickupValidCardTitle")}>
          <KeyValue
            items={[
              [t("thRecipient"), `${verified.recipient?.full_name ?? verified.recipient_hint} (${verified.recipient?.institutional_id ?? "–"})`],
              [t("thPackage"), verified.internal_code],
              [t("thShelf"), verified.storage_location?.code ?? "–"],
              [t("thCourier"), verified.courier_name],
            ]}
          />
          <p className="mt-4 text-sm text-muted">{t("pickupFetchNotice")}</p>
          <Button
            className="mt-4"
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
    </div>
  );
}
