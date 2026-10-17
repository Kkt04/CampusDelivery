import { FormEvent, useState } from "react";
import { newIdempotencyKey } from "../../api/client";
import { packagesApi } from "../../api/endpoints";
import type { Package, PackageCondition, PackageSize, UserBrief } from "../../api/types";
import { LearnerPicker } from "../../components/LearnerPicker";
import { StatusBadge } from "../../components/StatusBadge";
import { Alert, Button, Card, ErrorAlert, Field, PageHeader, TextLink } from "../../components/ui";
import { useAction } from "../../lib/useApi";

const COURIERS = ["Amazon Logistics", "BlueDart", "Delhivery", "DTDC", "Ekart", "India Post", "Shadowfax", "Xpressbees"];

function nowLocal(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

const EMPTY = { courier: "", tracking: "", unknownRecipient: false, hint: "", size: "SMALL" as PackageSize,
  condition: "GOOD" as PackageCondition, conditionNotes: "", arrivedAt: nowLocal(), notes: "" };

export function RegisterPackage() {
  const [form, setForm] = useState(EMPTY);
  const [learner, setLearner] = useState<UserBrief | null>(null);
  const [created, setCreated] = useState<Package | null>(null);
  // One key per form submission: a retry after a dropped connection reuses it, so the package is never registered twice.
  const [idemKey, setIdemKey] = useState(newIdempotencyKey);
  const set = <K extends keyof typeof EMPTY>(k: K, v: (typeof EMPTY)[K]) => setForm((f) => ({ ...f, [k]: v }));

  const submit = useAction(() => packagesApi.register({
    courier_name: form.courier.trim(),
    tracking_id: form.tracking.trim() || null,
    recipient_institutional_id: form.unknownRecipient ? null : learner?.institutional_id ?? null,
    recipient_hint: form.unknownRecipient ? form.hint.trim() || null : learner?.full_name ?? null,
    size: form.size,
    condition: form.condition,
    condition_notes: form.condition === "DAMAGED" ? form.conditionNotes.trim() || null : null,
    arrived_at: form.arrivedAt ? new Date(form.arrivedAt).toISOString() : null,
    notes: form.notes.trim() || null,
  }, idemKey));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const pkg = await submit.run();
    if (pkg) setCreated(pkg);
  }

  function reset() {
    setForm({ ...EMPTY, arrivedAt: nowLocal() });
    setLearner(null);
    setCreated(null);
    setIdemKey(newIdempotencyKey());
  }

  const fe = submit.error?.fieldErrors ?? {};
  const duplicate = submit.error?.code === "DUPLICATE_TRACKING_ID" ? (submit.error.details as { existing_package_id: number }) : null;

  if (created) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <PageHeader title="Package registered" />
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="code-text text-xl">{created.internal_code}</p>
              <p className="text-sm text-muted">{created.courier_name}, for {created.recipient?.full_name ?? created.recipient_hint}</p>
            </div>
            <StatusBadge status={created.status} />
          </div>
          {created.status === "UNIDENTIFIED" && <div className="mt-4"><Alert tone="warn">Recipient not identified. An incident was opened so operations can follow up.</Alert></div>}
          {created.status === "DAMAGED" && <div className="mt-4"><Alert tone="warn">Held as damaged. An incident was opened for review.</Alert></div>}
          <div className="mt-5 flex flex-wrap gap-3">
            <TextLink to={`/security/packages/${created.id}`}>Assign storage now</TextLink>
            <button className="text-sm font-semibold text-muted hover:text-ink" onClick={reset}>Register another package</button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Register a package" description="Record the parcel as the courier hands it over. Required fields are marked." />
      <form onSubmit={onSubmit} className="space-y-6" noValidate>
        {submit.error && !duplicate && <ErrorAlert error={submit.error} />}
        {duplicate && (
          <Alert tone="warn" title={submit.error!.message}>
            The attempt was logged. <TextLink to={`/security/packages/${duplicate.existing_package_id}`}>Open the existing package</TextLink>
          </Alert>
        )}

        <Card title="Shipment">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Courier (required)" htmlFor="courier" error={fe.courier_name}>
              <input id="courier" list="couriers" className="input" value={form.courier} onChange={(e) => set("courier", e.target.value)} />
              <datalist id="couriers">{COURIERS.map((c) => <option key={c} value={c} />)}</datalist>
            </Field>
            <Field label="Tracking ID" htmlFor="tracking" error={fe.tracking_id} hint="Leave blank if the label has none.">
              <input id="tracking" className="input" value={form.tracking} onChange={(e) => set("tracking", e.target.value)} />
            </Field>
            <Field label="Arrived at" htmlFor="arrived" error={fe.arrived_at}>
              <input id="arrived" type="datetime-local" className="input" value={form.arrivedAt} max={nowLocal()} onChange={(e) => set("arrivedAt", e.target.value)} />
            </Field>
            <Field label="Size" htmlFor="size">
              <select id="size" className="input" value={form.size} onChange={(e) => set("size", e.target.value as PackageSize)}>
                <option value="SMALL">Small (envelope, small box)</option>
                <option value="MEDIUM">Medium (shoebox)</option>
                <option value="LARGE">Large (bulky)</option>
              </select>
            </Field>
          </div>
        </Card>

        <Card title="Recipient">
          <div className="space-y-4">
            {!form.unknownRecipient && (
              <Field label="Learner (required)" htmlFor="learner" error={fe.recipient_institutional_id ?? (submit.error?.code === "LEARNER_NOT_FOUND" ? submit.error.message : undefined)}>
                <LearnerPicker id="learner" value={learner} onChange={setLearner} />
              </Field>
            )}
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4 accent-brand" checked={form.unknownRecipient}
                onChange={(e) => { set("unknownRecipient", e.target.checked); setLearner(null); }} />
              I can’t match the label to a learner
            </label>
            {form.unknownRecipient && (
              <Field label="What the label says (required)" htmlFor="hint" hint="The package goes to the unidentified queue for follow-up.">
                <input id="hint" className="input" value={form.hint} onChange={(e) => set("hint", e.target.value)} placeholder="Name, hostel, phone as written" />
              </Field>
            )}
          </div>
        </Card>

        <Card title="Condition">
          <div className="space-y-4">
            <fieldset className="flex gap-6 text-sm">
              <legend className="sr-only">Condition</legend>
              {(["GOOD", "DAMAGED"] as const).map((c) => (
                <label key={c} className="flex items-center gap-2">
                  <input type="radio" name="condition" className="h-4 w-4 accent-brand" checked={form.condition === c} onChange={() => set("condition", c)} />
                  {c === "GOOD" ? "Looks intact" : "Damaged"}
                </label>
              ))}
            </fieldset>
            {form.condition === "DAMAGED" && (
              <Field label="Describe the damage (required)" htmlFor="damage">
                <textarea id="damage" className="input min-h-20" value={form.conditionNotes} onChange={(e) => set("conditionNotes", e.target.value)} />
              </Field>
            )}
            <Field label="Notes for staff" htmlFor="notes">
              <input id="notes" className="input" value={form.notes} onChange={(e) => set("notes", e.target.value)} placeholder="e.g. fragile, keep upright" />
            </Field>
          </div>
        </Card>

        <Button type="submit" pending={submit.pending}
          disabled={!form.courier.trim() || (form.unknownRecipient ? !form.hint.trim() : !learner) || (form.condition === "DAMAGED" && !form.conditionNotes.trim())}>
          Register package
        </Button>
      </form>
    </div>
  );
}
