import { FormEvent, useState } from "react";
import { storageApi } from "../../api/endpoints";
import type { PackageSize, StorageLocation } from "../../api/types";
import { Alert, Button, Card, ErrorAlert, Field, PageHeader, Spinner } from "../../components/ui";
import { sentenceCase } from "../../lib/format";
import { useAction, useApi } from "../../lib/useApi";

export function StorageManagement() {
  const list = useApi(() => storageApi.list(), []);
  const [form, setForm] = useState({ code: "", description: "", capacity: "10", size: "MEDIUM" as PackageSize });
  const create = useAction(() => storageApi.create({ code: form.code.trim(), description: form.description.trim() || undefined,
    capacity: Number(form.capacity), max_package_size: form.size }));

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (await create.run()) { setForm({ code: "", description: "", capacity: "10", size: "MEDIUM" }); void list.reload(); }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Storage" description="Shelves and bays at Gate No. 2. A closed location keeps its packages but accepts no new ones." />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <Card title="Locations" bodyClass="p-0">
          {list.loading && !list.data ? <div className="px-5"><Spinner /></div>
            : list.error ? <div className="p-5"><ErrorAlert error={list.error} onRetry={list.reload} /></div>
            : (
              <div className="overflow-x-auto">
                <table className="table-base">
                  <thead><tr><th>Location</th><th>Holds up to</th><th>In use</th><th>Capacity</th><th>Status</th><th /></tr></thead>
                  <tbody>{list.data!.map((l) => <LocationRow key={l.id} location={l} onChanged={list.reload} />)}</tbody>
                </table>
              </div>
            )}
        </Card>
        <Card title="Add a location">
          <form className="space-y-4" onSubmit={onCreate}>
            <ErrorAlert error={create.error} />
            <Field label="Code" htmlFor="code" error={create.error?.fieldErrors.code} hint="Letters, digits and dashes, e.g. G2-M3.">
              <input id="code" className="input uppercase" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </Field>
            <Field label="Description" htmlFor="desc">
              <input id="desc" className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Capacity" htmlFor="cap" error={create.error?.fieldErrors.capacity}>
                <input id="cap" type="number" min={1} max={500} className="input" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} />
              </Field>
              <Field label="Largest size" htmlFor="size">
                <select id="size" className="input" value={form.size} onChange={(e) => setForm({ ...form, size: e.target.value as PackageSize })}>
                  <option value="SMALL">Small</option><option value="MEDIUM">Medium</option><option value="LARGE">Large</option>
                </select>
              </Field>
            </div>
            <Button type="submit" pending={create.pending} disabled={!form.code.trim()}>Add location</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}

function LocationRow({ location: l, onChanged }: { location: StorageLocation; onChanged: () => void }) {
  const [capacity, setCapacity] = useState(String(l.capacity));
  const [message, setMessage] = useState<string | null>(null);
  const update = useAction((body: Parameters<typeof storageApi.update>[1]) => storageApi.update(l.id, body));
  const pct = Math.round((l.occupied_count / l.capacity) * 100);

  async function save(body: Parameters<typeof storageApi.update>[1], done: string) {
    setMessage(null);
    if (await update.run(body)) { setMessage(done); onChanged(); }
  }

  return (
    <>
      <tr>
        <td><p className="code-text">{l.code}</p><p className="text-xs text-muted">{l.description}</p></td>
        <td>{sentenceCase(l.max_package_size)}</td>
        <td className="min-w-32">
          <div className="flex items-center gap-2">
            <div className="h-2 w-16 overflow-hidden rounded-full bg-paper"><div className={`h-full ${pct >= 100 ? "bg-danger" : "bg-brand"}`} style={{ width: `${pct}%` }} /></div>
            <span className="text-xs">{l.occupied_count}</span>
          </div>
        </td>
        <td>
          <form className="flex gap-1" onSubmit={(e) => { e.preventDefault(); void save({ capacity: Number(capacity) }, "Capacity saved."); }}>
            <input aria-label={`Capacity of ${l.code}`} type="number" min={1} className="input w-20 py-1" value={capacity} onChange={(e) => setCapacity(e.target.value)} />
            {Number(capacity) !== l.capacity && <Button type="submit" variant="secondary" className="py-1" pending={update.pending}>Save</Button>}
          </form>
        </td>
        <td>{l.is_active ? <span className="text-sm font-semibold text-brand-strong">Open</span> : <span className="text-sm font-semibold text-muted">Closed</span>}</td>
        <td className="text-right">
          <Button variant={l.is_active ? "danger" : "secondary"} className="py-1" pending={update.pending}
            onClick={() => save({ is_active: !l.is_active }, l.is_active ? "Location closed to new packages." : "Location reopened.")}>
            {l.is_active ? "Close" : "Reopen"}
          </Button>
        </td>
      </tr>
      {(update.error || message) && (
        <tr><td colSpan={6} className="pt-0">{update.error ? <ErrorAlert error={update.error} /> : <Alert tone="success">{message}</Alert>}</td></tr>
      )}
    </>
  );
}
