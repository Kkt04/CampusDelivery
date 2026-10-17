import { useState } from "react";
import { pickupApi } from "../../api/endpoints";
import { Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner, TextLink } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { useApi } from "../../lib/useApi";

export function PickupHistory() {
  const [page, setPage] = useState(1);
  const list = useApi(() => pickupApi.history(page), [page]);
  return (
    <div>
      <PageHeader title="Pickup history" description="Every package handed over to you, with the time and shelf it came from." />
      <Card bodyClass="p-0">
        {list.loading && !list.data ? <div className="px-5"><Spinner /></div>
          : list.error ? <div className="p-5"><ErrorAlert error={list.error} onRetry={list.reload} /></div>
          : list.data!.items.length === 0 ? <EmptyState title="No collections yet">Packages you collect will be listed here.</EmptyState>
          : (
            <div className="overflow-x-auto">
              <table className="table-base">
                <thead><tr><th>Package</th><th>Courier</th><th>Shelf</th><th>Collected</th></tr></thead>
                <tbody>
                  {list.data!.items.map((r) => (
                    <tr key={r.id}>
                      <td><TextLink to={`/learner/packages/${r.package_id}`}>{r.internal_code}</TextLink></td>
                      <td>{r.courier_name}</td>
                      <td className="code-text">{r.storage_location_code ?? "–"}</td>
                      <td>{formatDateTime(r.collected_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <Pagination page={page} pageSize={list.data!.page_size} total={list.data!.total} onPage={setPage} />
            </div>
          )}
      </Card>
    </div>
  );
}
