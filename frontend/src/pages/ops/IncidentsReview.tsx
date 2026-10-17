import { IncidentList } from "../../components/IncidentList";
import { PageHeader } from "../../components/ui";

export function IncidentsReview() {
  return (
    <div>
      <PageHeader title="Incidents" description="Reports from security and learners. Resolve each one with a note describing what was done." />
      <IncidentList canResolve packageBase="/ops/packages" />
    </div>
  );
}
