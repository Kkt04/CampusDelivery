import { FormEvent, useState } from "react";
import { usersApi } from "../../api/endpoints";
import type { Role, User } from "../../api/types";
import { useUser } from "../../auth/AuthContext";
import { Alert, Button, Card, EmptyState, ErrorAlert, Field, PageHeader, Pagination, Spinner } from "../../components/ui";
import { formatDate } from "../../lib/format";
import { useAction, useApi } from "../../lib/useApi";

const ROLE_LABEL: Record<Role, string> = { LEARNER: "Learner", SECURITY: "Security", ADMIN: "Operations admin" };

export function UsersPage() {
  const me = useUser();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState({ q: "", role: "" as Role | "" });
  const [page, setPage] = useState(1);
  const list = useApi(() => usersApi.list({ q: search.q || undefined, role: search.role || undefined, page }), [search, page]);
  const [form, setForm] = useState({ institutional_id: "", full_name: "", email: "", phone: "", role: "SECURITY" as Role, password: "" });
  const [created, setCreated] = useState<User | null>(null);
  const create = useAction(() => usersApi.create({ ...form, phone: form.phone || undefined }));
  const toggle = useAction((u: User) => usersApi.update(u.id, { is_active: !u.is_active }));

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    const u = await create.run();
    if (u) { setCreated(u); setForm({ institutional_id: "", full_name: "", email: "", phone: "", role: "SECURITY", password: "" }); void list.reload(); }
  }
  const fe = create.error?.fieldErrors ?? {};

  return (
    <div className="space-y-6">
      <PageHeader title="Users" description="Create staff and learner accounts. Deactivating an account signs the person out on their next request." />
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <Card bodyClass="p-0" title="Accounts" actions={
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setPage(1); setSearch({ ...search, q }); }}>
            <input aria-label="Search users" className="input w-40 py-1" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
            <select aria-label="Role" className="input w-auto py-1" value={search.role} onChange={(e) => { setPage(1); setSearch({ ...search, role: e.target.value as Role | "" }); }}>
              <option value="">All roles</option>{(Object.keys(ROLE_LABEL) as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
            </select>
          </form>}>
          <ErrorAlert error={toggle.error} />
          {list.loading && !list.data ? <div className="px-5"><Spinner /></div>
            : list.error ? <div className="p-5"><ErrorAlert error={list.error} onRetry={list.reload} /></div>
            : list.data!.items.length === 0 ? <EmptyState title="No users match" />
            : (
              <div className="overflow-x-auto">
                <table className="table-base">
                  <thead><tr><th>Name</th><th>ID</th><th>Role</th><th>Since</th><th>Status</th><th /></tr></thead>
                  <tbody>
                    {list.data!.items.map((u) => (
                      <tr key={u.id}>
                        <td><p className="font-medium">{u.full_name}</p><p className="text-xs text-muted">{u.email}</p></td>
                        <td className="code-text">{u.institutional_id}</td>
                        <td>{ROLE_LABEL[u.role]}</td>
                        <td>{formatDate(u.created_at)}</td>
                        <td className={u.is_active ? "text-brand-strong" : "text-muted"}>{u.is_active ? "Active" : "Deactivated"}</td>
                        <td className="text-right">
                          {u.id !== me.id && (
                            <Button variant={u.is_active ? "danger" : "secondary"} className="py-1" onClick={async () => { if (await toggle.run(u)) void list.reload(); }}>
                              {u.is_active ? "Deactivate" : "Reactivate"}
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <Pagination page={page} pageSize={list.data!.page_size} total={list.data!.total} onPage={setPage} />
              </div>
            )}
        </Card>

        <Card title="Create an account">
          <form className="space-y-3" onSubmit={onCreate} noValidate>
            {created && <Alert tone="success">Created {created.full_name} ({created.institutional_id}).</Alert>}
            <ErrorAlert error={create.error} />
            <Field label="Institutional ID" htmlFor="iid" error={fe.institutional_id}>
              <input id="iid" className="input uppercase" value={form.institutional_id} onChange={(e) => setForm({ ...form, institutional_id: e.target.value })} />
            </Field>
            <Field label="Full name" htmlFor="name" error={fe.full_name}>
              <input id="name" className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </Field>
            <Field label="Email" htmlFor="email" error={fe.email}>
              <input id="email" type="email" className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Phone (optional)" htmlFor="phone" error={fe.phone}>
              <input id="phone" className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </Field>
            <Field label="Role" htmlFor="role">
              <select id="role" className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
                {(Object.keys(ROLE_LABEL) as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </select>
            </Field>
            <Field label="Temporary password" htmlFor="pw" error={fe.password} hint="At least 8 characters, mixing letters with numbers or symbols.">
              <input id="pw" type="password" autoComplete="new-password" className="input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </Field>
            <Button type="submit" pending={create.pending}>Create account</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
