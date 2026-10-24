import { FormEvent, useState } from "react";
import { packagesApi } from "../../api/endpoints";
import type { Package, PackageSize } from "../../api/types";
import { StatusBadge } from "../../components/StatusBadge";
import { Alert, Button, Card, EmptyState, ErrorAlert, Field, PageHeader, Spinner, TextLink } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import { formatDateTime } from "../../lib/format";
import { useAction, useApi } from "../../lib/useApi";

const COURIERS = ["Amazon Logistics", "BlueDart", "Delhivery", "DTDC", "Ekart", "India Post", "Shadowfax", "Xpressbees"];

const COMMON_REASONS = [
  "Wrong item received",
  "Product is defective or damaged",
  "Size or fit issue",
  "Item no longer needed / changed mind",
  "Courier pickup arranged by seller",
];

export function ReturnParcelPage() {
  const { t } = useLanguage();
  const [selectedPkgId, setSelectedPkgId] = useState<string>("custom");
  const [courier, setCourier] = useState("");
  const [trackingId, setTrackingId] = useState("");
  const [reason, setReason] = useState(COMMON_REASONS[0]);
  const [customReason, setCustomReason] = useState("");
  const [size, setSize] = useState<PackageSize>("SMALL");
  const [notes, setNotes] = useState("");
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Load learner's active packages that could be returned
  const myPackages = useApi(
    () =>
      packagesApi.list({
        status: ["VERIFIED", "STORED", "READY_FOR_PICKUP", "PICKUP_REQUESTED"],
        page_size: 50,
      }),
    []
  );

  // Load learner's returns list
  const returnsList = useApi(
    () =>
      packagesApi.list({
        status: ["RETURN_REQUESTED", "RETURNED"],
        page_size: 20,
      }),
    []
  );

  const submitAction = useAction(async () => {
    const finalReason = reason === "Other" ? customReason.trim() : reason;
    if (!finalReason) throw new Error("Please specify a reason for the return.");

    let res: Package;
    if (selectedPkgId !== "custom") {
      res = await packagesApi.initiateReturn({
        package_id: Number(selectedPkgId),
        reason: finalReason,
        notes: notes.trim() || null,
      });
    } else {
      if (!courier.trim()) throw new Error("Please select or enter the courier name.");
      res = await packagesApi.initiateReturn({
        courier_name: courier.trim(),
        tracking_id: trackingId.trim() || null,
        reason: finalReason,
        size,
        notes: notes.trim() || null,
      });
    }
    return res;
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSuccessMsg(null);
    const created = await submitAction.run();
    if (created) {
      setSuccessMsg(t("returnSuccessNotice") + ` (${created.internal_code})`);
      setSelectedPkgId("custom");
      setCourier("");
      setTrackingId("");
      setCustomReason("");
      setNotes("");
      void returnsList.reload();
      void myPackages.reload();
    }
  }

  const eligiblePackages = myPackages.data?.items ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        title={t("returnPageTitle")}
        description={t("returnPageSubtitle")}
      />

      {successMsg && <Alert tone="success">{successMsg}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Return Submission Form */}
        <Card title={t("initiateParcelReturn")}>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <ErrorAlert error={submitAction.error} />

            <Field label={t("thPackage")} htmlFor="package-select">
              <select
                id="package-select"
                className="input"
                value={selectedPkgId}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedPkgId(val);
                  if (val !== "custom") {
                    const found = eligiblePackages.find((p) => p.id === Number(val));
                    if (found) {
                      setCourier(found.courier_name);
                      setTrackingId(found.tracking_id ?? "");
                    }
                  }
                }}
              >
                <option value="custom">+ Manual / Custom Package</option>
                {eligiblePackages.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.internal_code} — {p.courier_name} {p.tracking_id ? `(${p.tracking_id})` : ""}
                  </option>
                ))}
              </select>
            </Field>

            {selectedPkgId === "custom" && (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label={t("regCourierLabel")} htmlFor="ret-courier">
                    <input
                      id="ret-courier"
                      list="return-couriers"
                      className="input"
                      placeholder="Amazon, BlueDart, Delhivery..."
                      value={courier}
                      onChange={(e) => setCourier(e.target.value)}
                      required
                    />
                    <datalist id="return-couriers">
                      {COURIERS.map((c) => (
                        <option key={c} value={c} />
                      ))}
                    </datalist>
                  </Field>

                  <Field label={t("regTrackingLabel")} htmlFor="ret-tracking" hint={t("regTrackingHint")}>
                    <input
                      id="ret-tracking"
                      className="input"
                      placeholder="e.g. RET-987654"
                      value={trackingId}
                      onChange={(e) => setTrackingId(e.target.value)}
                    />
                  </Field>
                </div>

                <Field label={t("regSizeLabel")} htmlFor="ret-size">
                  <select id="ret-size" className="input" value={size} onChange={(e) => setSize(e.target.value as PackageSize)}>
                    <option value="SMALL">{t("regSizeSmall")}</option>
                    <option value="MEDIUM">{t("regSizeMedium")}</option>
                    <option value="LARGE">{t("regSizeLarge")}</option>
                  </select>
                </Field>
              </>
            )}

            <Field label={t("returnReasonLabel")} htmlFor="ret-reason">
              <select id="ret-reason" className="input" value={reason} onChange={(e) => setReason(e.target.value)}>
                {COMMON_REASONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
                <option value="Other">Other</option>
              </select>
            </Field>

            {reason === "Other" && (
              <Field label={t("returnReasonLabel")} htmlFor="ret-custom-reason">
                <input
                  id="ret-custom-reason"
                  className="input"
                  placeholder={t("returnReasonPlaceholder")}
                  value={customReason}
                  onChange={(e) => setCustomReason(e.target.value)}
                  required
                />
              </Field>
            )}

            <Field label={t("thRecipient")} htmlFor="ret-notes" hint="Optional notes or courier instructions">
              <textarea
                id="ret-notes"
                className="input min-h-20"
                placeholder="e.g. Courier agent will ask for barcode on top of the box"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </Field>

            <Button
              type="submit"
              className="w-full"
              pending={submitAction.pending}
              disabled={selectedPkgId === "custom" && !courier.trim()}
            >
              {t("returnSubmitBtn")}
            </Button>
          </form>
        </Card>

        {/* How it works info card */}
        <div className="space-y-6">
          <Card title="Gate No. 2 Return Service">
            <ol className="space-y-3 text-sm text-ink/90">
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-100 font-bold text-primary-700">
                  1
                </span>
                <div>
                  <strong>{t("submit")}:</strong> {t("returnPageSubtitle")}
                </div>
              </li>
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-100 font-bold text-primary-700">
                  2
                </span>
                <div>
                  <strong>Drop Parcel:</strong> Drop the parcel at Gate No. 2 with the return label clearly attached.
                </div>
              </li>
              <li className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-100 font-bold text-primary-700">
                  3
                </span>
                <div>
                  <strong>Handover:</strong> When the courier pickup partner arrives, security completes the handover.
                </div>
              </li>
            </ol>
          </Card>
        </div>
      </div>

      {/* Return Requests History */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">{t("activeReturnRequests")}</h2>
        <Card bodyClass="p-0">
          {returnsList.loading && !returnsList.data ? (
            <div className="px-5 py-6">
              <Spinner label={t("loading")} />
            </div>
          ) : returnsList.error ? (
            <div className="p-5">
              <ErrorAlert error={returnsList.error} onRetry={returnsList.reload} />
            </div>
          ) : returnsList.data!.items.length === 0 ? (
            <EmptyState title={t("noData")} />
          ) : (
            <div className="overflow-x-auto">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>{t("thPackage")}</th>
                    <th>{t("thCourier")}</th>
                    <th>{t("returnReasonLabel")}</th>
                    <th>{t("thStatus")}</th>
                    <th>{t("thArrived")}</th>
                  </tr>
                </thead>
                <tbody>
                  {returnsList.data!.items.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <TextLink to={`/learner/packages/${p.id}`}>
                          <span className="code-text font-bold text-primary-700">{p.internal_code}</span>
                        </TextLink>
                        {p.tracking_id && <p className="text-xs text-muted">{p.tracking_id}</p>}
                      </td>
                      <td>{p.courier_name}</td>
                      <td>
                        <p className="font-medium text-ink">{p.notes ?? t("statusReturnRequested")}</p>
                      </td>
                      <td>
                        <StatusBadge status={p.status} learner />
                      </td>
                      <td className="whitespace-nowrap">{formatDateTime(p.arrived_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </section>
    </div>
  );
}
