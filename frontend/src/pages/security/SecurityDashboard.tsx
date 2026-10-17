import { Link } from "react-router-dom";
import { packagesApi, reportsApi } from "../../api/endpoints";
import type { PackageStatus } from "../../api/types";
import { CountStrip } from "../../components/CountStrip";
import { PackageTable } from "../../components/PackageTable";
import { Card, EmptyState, ErrorAlert, PageHeader, Spinner } from "../../components/ui";
import { useApi } from "../../lib/useApi";

function Queue({ title, statuses, empty }: { title: string; statuses: PackageStatus[]; empty: string }) {
  const list = useApi(() => packagesApi.list({ status: statuses, page_size: 5 }), []);
  return (
    <Card title={`${title}${list.data ? ` (${list.data.total})` : ""}`} bodyClass="p-0">
      {list.loading ? <div className="px-5"><Spinner /></div> : list.error ? <div className="p-5"><ErrorAlert error={list.error} /></div>
        : list.data!.items.length === 0 ? <EmptyState title={empty} />
        : <PackageTable packages={list.data!.items} basePath="/security/packages" />}
    </Card>
  );
}

export function SecurityDashboard() {
  const stats = useApi(() => reportsApi.dashboard(), []);
  const s = stats.data;
  return (
    <div className="space-y-6">
      <PageHeader title="Gate No. 2" description="Today’s intake and the queues that need a guard."
        actions={<>
          <Link to="/security/register" className="rounded-md bg-brand px-3.5 py-2 text-sm font-semibold text-white hover:bg-brand-strong">Register package</Link>
          <Link to="/security/pickup" className="rounded-md border border-line bg-white px-3.5 py-2 text-sm font-semibold hover:border-muted/50">Hand over a package</Link>
        </>} />
      {stats.error ? <ErrorAlert error={stats.error} onRetry={stats.reload} /> : !s ? <Spinner /> : (
        <CountStrip items={[
          { label: "Received today", value: s.received_today },
          { label: "Collected today", value: s.collected_today },
          { label: "In custody", value: s.in_custody, to: "/security/packages" },
          { label: "Awaiting storage", value: s.by_status.VERIFIED, tone: "brand" },
          { label: "Unidentified", value: s.by_status.UNIDENTIFIED, tone: "warn" },
          { label: "Held as damaged", value: s.by_status.DAMAGED, tone: "danger" },
        ]} />
      )}
      <Queue title="Waiting for a shelf" statuses={["VERIFIED"]} empty="Every verified package has a shelf." />
      <Queue title="Needs identification or review" statuses={["UNIDENTIFIED", "DAMAGED", "UNDER_INVESTIGATION"]} empty="No exceptions waiting." />
      <Queue title="Stored, not yet marked ready" statuses={["STORED"]} empty="Nothing waiting to be marked ready." />
    </div>
  );
}
