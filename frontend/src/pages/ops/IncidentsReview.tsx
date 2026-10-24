import { IncidentList } from "../../components/IncidentList";
import { PageHeader } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";

export function IncidentsReview() {
  const { t } = useLanguage();
  return (
    <div>
      <PageHeader
        title={t("incidentsTitle")}
        description={t("incidentsOpsDesc")}
      />
      <IncidentList canResolve packageBase="/ops/packages" />
    </div>
  );
}
