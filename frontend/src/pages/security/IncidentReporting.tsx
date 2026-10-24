import { FormEvent, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { incidentsApi, packagesApi } from "../../api/endpoints";
import type { IncidentType } from "../../api/types";
import { IncidentList } from "../../components/IncidentList";
import { Alert, Button, Card, ErrorAlert, Field, PageHeader } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import type { TranslationDictionary } from "../../i18n/types";
import { useAction, useApi } from "../../lib/useApi";

const TYPES: { value: IncidentType; labelKey: keyof TranslationDictionary }[] = [
  { value: "DAMAGE", labelKey: "incidentTypeDamage" },
  { value: "UNIDENTIFIED_RECIPIENT", labelKey: "incidentTypeUnidentified" },
  { value: "MISSING_PACKAGE", labelKey: "incidentTypeMissing" },
  { value: "OPERATIONAL", labelKey: "incidentTypeOperational" },
];

export function IncidentReporting() {
  const { t } = useLanguage();
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
    if (incident) {
      setDone(incident.id);
      setDescription("");
      setEscalate(false);
      setRefresh((r) => r + 1);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("incidentsTitle")}
        description={t("incidentsSecurityDesc")}
      />
      <div className="grid gap-6 lg:grid-cols-[400px_1fr]">
        <Card title={t("reportIncidentCard")}>
          <form className="space-y-4" onSubmit={onSubmit}>
            {done && <Alert tone="success">Incident #{done} recorded.</Alert>}
            <ErrorAlert error={submit.error} />
            {preset.data ? (
              <p className="text-sm">
                {t("thPackage")} <strong className="code-text font-bold text-primary-700">{preset.data.internal_code}</strong>
              </p>
            ) : (
              <Field label={t("pickupPkgCodeLabel")} htmlFor="code" hint="Optional, e.g. PKG-...">
                <input id="code" className="input code-text uppercase" value={code} onChange={(e) => setCode(e.target.value)} />
              </Field>
            )}
            <Field label={t("thAction")} htmlFor="type">
              <select id="type" className="input" value={type} onChange={(e) => setType(e.target.value as IncidentType)}>
                {TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {t(item.labelKey)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t("pkgReportDescLabel")} htmlFor="desc" error={submit.error?.fieldErrors.description}>
              <textarea
                id="desc"
                className="input min-h-28"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t("pkgReportDescPlaceholder")}
              />
            </Field>
            {(preset.data || code.trim()) && (
              <label className="flex items-start gap-2 text-sm text-ink cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  checked={escalate}
                  onChange={(e) => setEscalate(e.target.checked)}
                />
                Put package under investigation
              </label>
            )}
            <Button type="submit" pending={submit.pending} disabled={description.trim().length < 5}>
              {t("reportIncidentBtn")}
            </Button>
          </form>
        </Card>
        <IncidentList key={refresh} canResolve={false} />
      </div>
    </div>
  );
}
