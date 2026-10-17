import { FormEvent, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { incidentsApi, packagesApi } from "../../api/endpoints";
import type { IncidentType } from "../../api/types";
import { IncidentList } from "../../components/IncidentList";
import { Alert, Button, Card, ErrorAlert, Field, PageHeader } from "../../components/ui";
import { useAction, useApi } from "../../lib/useApi";

const TYPES: { value: IncidentType; label: string }[] = [
  { value: "DAMAGE", label: "Damage" },
  { value: "UNIDENTIFIED_RECIPIENT", label: "Unidentified recipient" },
  { value: "MISSING_PACKAGE", label: "Package missing from shelf" },
  { value: "OPERATIONAL", label: "Other operational issue" },
];

export function IncidentReporting() {
  const [params] = useSearchParams();
  const presetId = params.get("package");
  const preset = useApi(() => (presetId ? packagesApi.get(Number(presetId)) : Promise.resolve(null)), [presetId]);
  const [code, setCode] = useState("");
  const [type, setType] = useState<IncidentType>("OPERATIONAL");
  const [description, setDescription] = useState("");
  const [escalate, setEscalate] = useState(false);
  const [done, setDone] = useState<number | null>(null);
  const [refresh, setRefresh] = useState(0);

  const submit = useAction(async () => {
    let packageId: number | null = preset.data?.id ?? null;
    if (!packageId && code.trim()) {
      const found = await packagesApi.list({ q: code.trim(), page_size: 5 });
      const match = found.items.find((p) => p.internal_code === code.trim().toUpperCase());
      if (!match) throw new ApiError(404, "NOT_FOUND", `No package with code ${code.trim().toUpperCase()}`);
      packageId = match.id;
    }
    return incidentsApi.create({ package_id: packageId, type, description: description.trim(), escalate: escalate && !!packageId });
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const incident = await submit.run();
    if (incident) { setDone(incident.id); setDescription(""); setEscalate(false); setRefresh((r) => r + 1); }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Incidents" description="Record damage, unidentified recipients and anything unusual at the gate. Operations reviews every report." />
      <div className="grid gap-6 lg:grid-cols-[400px_1fr]">
        <Card title="Report an incident">
          <form className="space-y-4" onSubmit={onSubmit}>
            {done && <Alert tone="success">Incident #{done} recorded.</Alert>}
            <ErrorAlert error={submit.error} />
            {preset.data ? (
              <p className="text-sm">Package <strong className="code-text">{preset.data.internal_code}</strong></p>
            ) : (
              <Field label="Package code (optional)" htmlFor="code" hint="Leave blank for issues not tied to one package, e.g. a shift-change note.">
                <input id="code" className="input code-text uppercase" value={code} onChange={(e) => setCode(e.target.value)} />
              </Field>
            )}
            <Field label="Type" htmlFor="type">
              <select id="type" className="input" value={type} onChange={(e) => setType(e.target.value as IncidentType)}>
                {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Field>
            <Field label="What happened?" htmlFor="desc" error={submit.error?.fieldErrors.description}>
              <textarea id="desc" className="input min-h-28" value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            {(preset.data || code.trim()) && (
              <label className="flex items-start gap-2 text-sm">
                <input type="checkbox" className="mt-0.5 h-4 w-4 accent-brand" checked={escalate} onChange={(e) => setEscalate(e.target.checked)} />
                Put the package under investigation (blocks pickup until operations resolves it)
              </label>
            )}
            <Button type="submit" pending={submit.pending} disabled={description.trim().length < 5}>Record incident</Button>
          </form>
        </Card>
        <IncidentList key={refresh} canResolve={false} />
      </div>
    </div>
  );
}
