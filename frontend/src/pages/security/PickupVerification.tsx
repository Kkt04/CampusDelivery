import { FormEvent, useState } from "react";
import { newIdempotencyKey } from "../../api/client";
import { pickupApi } from "../../api/endpoints";
import type { Package, PickupInput, PickupRecord } from "../../api/types";
import { Alert, Button, Card, ErrorAlert, Field, KeyValue, PageHeader } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { useAction } from "../../lib/useApi";

export function PickupVerification() {
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
        <PageHeader title="Handed over" />
        <Alert tone="success" title={`${record.internal_code} collected`}>
          Recorded at {formatDateTime(record.collected_at)} by {record.handed_over_by?.full_name}. Shelf {record.storage_location_code ?? "–"} is free again.
        </Alert>
        <Button onClick={reset}>Next handover</Button>
      </div>
    );
  }

  const error = verify.error ?? complete.error;
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageHeader title="Pickup handover" description="Check the learner’s ID card, then enter the package code and their 6-digit pickup code." />
      <form onSubmit={onVerify} className="card space-y-4 p-5" noValidate>
        <ErrorAlert error={error} />
        <Field label="Package code" htmlFor="pkg" hint="Printed on the shelf label, e.g. PKG-261017-ABCDE.">
          <input id="pkg" className="input code-text uppercase" value={input.package_code} onChange={set("package_code")} autoComplete="off" />
        </Field>
        <Field label="Learner ID (from their ID card)" htmlFor="lrn">
          <input id="lrn" className="input uppercase" value={input.learner_institutional_id} onChange={set("learner_institutional_id")} autoComplete="off" />
        </Field>
        <Field label="Pickup code" htmlFor="code">
          <input id="code" className="input code-text text-lg tracking-[0.3em]" inputMode="numeric" maxLength={7} value={input.code}
            onChange={set("code")} autoComplete="one-time-code" />
        </Field>
        <Button type="submit" variant={verified ? "secondary" : "primary"} pending={verify.pending}
          disabled={!input.package_code || !input.learner_institutional_id || input.code.replace(/\D/g, "").length !== 6}>
          Check code
        </Button>
      </form>

      {verified && (
        <Card title="Code is valid">
          <KeyValue items={[
            ["Learner", `${verified.recipient?.full_name} (${verified.recipient?.institutional_id})`],
            ["Package", verified.internal_code],
            ["Shelf", verified.storage_location?.code ?? "–"],
            ["Courier", verified.courier_name],
          ]} />
          <p className="mt-4 text-sm text-muted">Fetch the package from the shelf and confirm the handover only once it is in the learner’s hands.</p>
          <Button className="mt-4" pending={complete.pending} onClick={async () => { const r = await complete.run(); if (r) setRecord(r); }}>
            Hand over package
          </Button>
        </Card>
      )}
    </div>
  );
}
