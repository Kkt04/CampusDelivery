import { FormEvent, useEffect, useState } from "react";
import { newIdempotencyKey } from "../../api/client";
import { packagesApi, storageApi } from "../../api/endpoints";
import type { Package, PackageSize, StorageLocation, UserBrief } from "../../api/types";
import { LearnerPicker } from "../../components/LearnerPicker";
import { StatusBadge } from "../../components/StatusBadge";
import { Alert, Button, Card, ErrorAlert, Field, PageHeader, TextLink } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { useAction } from "../../lib/useApi";

const COURIERS = ["Amazon Logistics", "BlueDart", "Delhivery", "DTDC", "Ekart", "India Post", "Shadowfax", "Xpressbees"];

function nowLocal(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

const EMPTY = {
  courier: "",
  tracking: "",
  unknownRecipient: false,
  hint: "",
  size: "SMALL" as PackageSize,
  arrivedAt: nowLocal(),
};

export function RegisterPackage() {
  const { t } = useLanguage();
  const [form, setForm] = useState(EMPTY);
  const [rackNumber, setRackNumber] = useState("");
  const [learner, setLearner] = useState<UserBrief | null>(null);
  const [created, setCreated] = useState<Package | null>(null);
  const [existingLocations, setExistingLocations] = useState<StorageLocation[]>([]);
  // One key per form submission: a retry after a dropped connection reuses it, so the package is never registered twice.
  const [idemKey, setIdemKey] = useState(newIdempotencyKey);
  const set = <K extends keyof typeof EMPTY>(k: K, v: (typeof EMPTY)[K]) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    storageApi.list(true).then(setExistingLocations).catch(() => {});
  }, []);

  const submit = useAction(async () => {
    const isUnlistedLearner = !form.unknownRecipient && learner && learner.id === 0;
    const recipientInstitutionalId = form.unknownRecipient || isUnlistedLearner ? null : learner?.institutional_id ?? null;
    const recipientHint = form.unknownRecipient
      ? (form.hint.trim() || null)
      : isUnlistedLearner
        ? `${learner.full_name} (${learner.institutional_id})`
        : (learner?.full_name ?? null);

    const pkg = await packagesApi.register({
      courier_name: form.courier.trim(),
      tracking_id: form.tracking.trim() || null,
      recipient_institutional_id: recipientInstitutionalId,
      recipient_hint: recipientHint,
      size: form.size,
      condition: "GOOD",
      condition_notes: null,
      arrived_at: form.arrivedAt ? new Date(form.arrivedAt).toISOString() : null,
      notes: null,
    }, idemKey);

    const trimmedRack = rackNumber.trim();
    if (trimmedRack) {
      let location = existingLocations.find(
        (l) => l.code.trim().toUpperCase() === trimmedRack.toUpperCase()
      );
      if (!location) {
        try {
          location = await storageApi.create({
            code: trimmedRack.toUpperCase(),
            capacity: 50,
            max_package_size: "LARGE",
          });
          setExistingLocations((prev) => [...prev, location!]);
        } catch {
          try {
            const all = await storageApi.list(false);
            location = all.find((l) => l.code.trim().toUpperCase() === trimmedRack.toUpperCase());
          } catch {
            // fallback
          }
        }
      }

      try {
        const stored = await packagesApi.assignStorage(pkg.id, location?.id ?? null, true);
        return stored;
      } catch {
        return pkg;
      }
    } else {
      try {
        const stored = await packagesApi.assignStorage(pkg.id, null, true);
        return stored;
      } catch {
        return pkg;
      }
    }
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const pkg = await submit.run();
    if (pkg) setCreated(pkg);
  }

  function reset() {
    setForm({ ...EMPTY, arrivedAt: nowLocal() });
    setRackNumber("");
    setLearner(null);
    setCreated(null);
    setIdemKey(newIdempotencyKey());
    storageApi.list(true).then(setExistingLocations).catch(() => {});
  }

  const fe = submit.error?.fieldErrors ?? {};
  const duplicate = submit.error?.code === "DUPLICATE_TRACKING_ID" ? (submit.error.details as { existing_package_id: number }) : null;

  if (created) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <PageHeader title={t("regSuccessTitle")} />
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="code-text text-xl font-bold text-ink">{created.internal_code}</p>
              <p className="text-sm text-muted">
                {created.courier_name}, for {created.recipient?.full_name ?? created.recipient_hint}
              </p>
            </div>
            <StatusBadge status={created.status} />
          </div>
          {created.storage_location && (
            <div className="mt-4 rounded-xl border border-primary-200 bg-primary-50 p-4 text-sm">
              <p className="font-semibold text-primary-900">
                {t("regStoredAtShelf")}{" "}
                <span className="code-text text-base font-bold text-primary-700 bg-white px-2.5 py-0.5 rounded-lg border border-primary-200 ml-1">
                  {created.storage_location.code}
                </span>
              </p>
              {created.status === "READY_FOR_PICKUP" && (
                <p className="mt-1.5 text-xs text-primary-800">{t("regReadyNotification")}</p>
              )}
            </div>
          )}
          {created.status === "UNIDENTIFIED" && (
            <div className="mt-4">
              <Alert tone="warn">
                Recipient not yet registered. When the student signs up or logs in with this ID, the package will automatically link to their account.
              </Alert>
            </div>
          )}
          <div className="mt-5 flex flex-wrap items-center gap-4">
            {!created.storage_location && (
              <TextLink to={`/security/packages/${created.id}`}>{t("regAssignStorageBtn")}</TextLink>
            )}
            <button
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary-700 hover:text-primary-800 hover:underline"
              onClick={reset}
            >
              <span>+</span> {t("regAnotherBtn")}
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title={t("regPageTitle")}
        description={t("regPageSubtitle")}
      />
      <form onSubmit={onSubmit} className="space-y-6" noValidate>
        {submit.error && !duplicate && <ErrorAlert error={submit.error} />}
        {duplicate && (
          <Alert tone="warn" title={submit.error!.message}>
            The attempt was logged. <TextLink to={`/security/packages/${duplicate.existing_package_id}`}>Open the existing package</TextLink>
          </Alert>
        )}

        {/* Shipment Details */}
        <Card title={t("regShipmentCard")}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("regCourierLabel")} htmlFor="courier" error={fe.courier_name}>
              <input
                id="courier"
                list="couriers"
                className="input"
                placeholder="Amazon Logistics, BlueDart, Delhivery..."
                value={form.courier}
                onChange={(e) => set("courier", e.target.value)}
                required
              />
              <datalist id="couriers">
                {COURIERS.map((c) => (
                  <option key={c} value={c} />
                ))}
              </datalist>
            </Field>
            <Field label={t("regTrackingLabel")} htmlFor="tracking" error={fe.tracking_id} hint={t("regTrackingHint")}>
              <input
                id="tracking"
                className="input"
                placeholder="e.g. 1Z9999999999999999"
                value={form.tracking}
                onChange={(e) => set("tracking", e.target.value)}
              />
            </Field>
            <Field label={t("regArrivedAtLabel")} htmlFor="arrived" error={fe.arrived_at}>
              <input
                id="arrived"
                type="datetime-local"
                className="input"
                value={form.arrivedAt}
                max={nowLocal()}
                onChange={(e) => set("arrivedAt", e.target.value)}
              />
            </Field>
            <Field label={t("regSizeLabel")} htmlFor="size">
              <select id="size" className="input" value={form.size} onChange={(e) => set("size", e.target.value as PackageSize)}>
                <option value="SMALL">{t("regSizeSmall")}</option>
                <option value="MEDIUM">{t("regSizeMedium")}</option>
                <option value="LARGE">{t("regSizeLarge")}</option>
              </select>
            </Field>
          </div>
        </Card>

        {/* Recipient Details */}
        <Card title={t("regRecipientCard")}>
          <div className="space-y-4">
            {!form.unknownRecipient && (
              <Field
                label={t("regLearnerLabel")}
                htmlFor="learner"
                error={fe.recipient_institutional_id ?? (submit.error?.code === "LEARNER_NOT_FOUND" ? submit.error.message : undefined)}
              >
                <LearnerPicker id="learner" value={learner} onChange={setLearner} />
              </Field>
            )}
            <label className="flex items-center gap-2 text-sm text-ink cursor-pointer">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                checked={form.unknownRecipient}
                onChange={(e) => {
                  set("unknownRecipient", e.target.checked);
                  setLearner(null);
                }}
              />
              {t("regUnknownCheckbox")}
            </label>
            {form.unknownRecipient && (
              <Field label={t("regUnknownHintLabel")} htmlFor="hint" hint={t("regUnknownHintHelp")}>
                <input
                  id="hint"
                  className="input"
                  value={form.hint}
                  onChange={(e) => set("hint", e.target.value)}
                  placeholder={t("regUnknownHintPlaceholder")}
                  required
                />
              </Field>
            )}
          </div>
        </Card>

        {/* Rack Number / Storage Card (Condition removed, Manual Rack added) */}
        <Card title={t("regStorageCard")}>
          <div className="space-y-3">
            <Field
              label={t("regRackLabel")}
              htmlFor="rackNumber"
              hint={t("regRackHint")}
            >
              <div className="relative">
                <input
                  id="rackNumber"
                  list="storage-racks"
                  className="input font-mono uppercase font-semibold text-primary-800 placeholder:normal-case placeholder:font-normal"
                  value={rackNumber}
                  onChange={(e) => setRackNumber(e.target.value)}
                  placeholder={t("regRackPlaceholder")}
                  required
                />
                <datalist id="storage-racks">
                  {existingLocations.map((loc) => (
                    <option key={loc.id} value={loc.code}>
                      {loc.code} ({loc.occupied_count}/{loc.capacity} {loc.description ? `- ${loc.description}` : ""})
                    </option>
                  ))}
                </datalist>
              </div>
            </Field>
            <p className="text-xs text-muted">
              {t("regReadyNotification")}
            </p>
          </div>
        </Card>

        <Button
          type="submit"
          pending={submit.pending}
          disabled={!form.courier.trim() || (form.unknownRecipient ? !form.hint.trim() : !learner) || !rackNumber.trim()}
        >
          {t("regSubmitBtn")}
        </Button>
      </form>
    </div>
  );
}
