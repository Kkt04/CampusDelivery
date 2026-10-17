import { FormEvent, useState } from "react";
import { reportsApi } from "../../api/endpoints";
import { Button, Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { useApi } from "../../lib/useApi";

const PRESETS = ["", "package.", "pickup.", "auth.", "storage.", "incident.", "user."];

export function AuditPage() {
  const [draft, setDraft] = useState({ action: "", entity_id: "", date_from: "", date_to: "" });
  const [filters, setFilters] = useState(draft);
  const [page, setPage] = useState(1);
  const list = useApi(() => reportsApi.audit({
    action: filters.action || undefined, entity_id: filters.entity_id || undefined,
    entity_type: filters.entity_id ? "package" : undefined,
    date_from: filters.date_from || undefined, date_to: filters.date_to || undefined, page }), [filters, page]);

  function onSubmit(e: FormEvent) { e.preventDefault(); setPage(1); setFilters(draft); }

  return (
    <div>
      <PageHeader title="Audit log" description="Every sensitive action, who did it and when. Entries cannot be edited or deleted." />
      <form onSubmit={onSubmit} className="card mb-4 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_1fr_auto] lg:items-end">
        <div>
          <label htmlFor="action" className="label">Action</label>
          <select id="action" className="input" value={draft.action} onChange={(e) => setDraft({ ...draft, action: e.target.value })}>
            {PRESETS.map((p) => <option key={p} value={p}>{p ? `${p}*` : "All actions"}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="pid" className="label">Package ID (number)</label>
          <input id="pid" inputMode="numeric" className="input" value={draft.entity_id} onChange={(e) => setDraft({ ...draft, entity_id: e.target.value.replace(/\D/g, "") })} />
        </div>
        <div><label htmlFor="df" className="label">From</label><input id="df" type="date" className="input" value={draft.date_from} onChange={(e) => setDraft({ ...draft, date_from: e.target.value })} /></div>
        <div><label htmlFor="dt" className="label">To</label><input id="dt" type="date" className="input" value={draft.date_to} onChange={(e) => setDraft({ ...draft, date_to: e.target.value })} /></div>
        <Button type="submit">Filter</Button>
      </form>
      <Card bodyClass="p-0">
        {list.loading && !list.data ? <div className="px-5"><Spinner /></div>
          : list.error ? <div className="p-5"><ErrorAlert error={list.error} onRetry={list.reload} /></div>
          : list.data!.items.length === 0 ? <EmptyState title="No audit entries match" />
          : (
            <div className="overflow-x-auto">
              <table className="table-base">
                <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Target</th><th>Details</th></tr></thead>
                <tbody>
                  {list.data!.items.map((a) => (
                    <tr key={a.id}>
                      <td className="whitespace-nowrap">{formatDateTime(a.created_at)}</td>
                      <td>{a.actor ? `${a.actor.full_name} (${a.actor.institutional_id})` : <span className="text-muted">Unknown</span>}</td>
                      <td className="whitespace-nowrap font-medium">{a.action}</td>
                      <td className="whitespace-nowrap">{a.entity_type} {a.entity_id ?? ""}</td>
                      <td className="max-w-md text-xs text-muted">
                        {a.details && Object.entries(a.details).map(([k, v]) => (
                          <span key={k} className="mr-3 inline-block">{k}: <span className="text-ink">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span></span>
                        ))}
                      </td>
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
