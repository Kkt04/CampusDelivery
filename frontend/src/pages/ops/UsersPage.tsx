import { FormEvent, useState } from "react";
import { usersApi } from "../../api/endpoints";
import type { Role, User } from "../../api/types";
import { useUser } from "../../auth/AuthContext";
import { Alert, Button, Card, EmptyState, ErrorAlert, Field, PageHeader, Pagination, Spinner } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";
import type { TranslationDictionary } from "../../i18n/types";
import { formatDate } from "../../lib/format";
import { useAction, useApi } from "../../lib/useApi";

const ROLE_KEYS: Record<Role, keyof TranslationDictionary> = {
  LEARNER: "roleLearner",
  SECURITY: "roleSecurity",
  ADMIN: "roleAdmin",
};

export function UsersPage() {
  const me = useUser();
  const { t } = useLanguage();
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
    if (u) {
      setCreated(u);
      setForm({ institutional_id: "", full_name: "", email: "", phone: "", role: "SECURITY", password: "" });
      void list.reload();
    }
  }
  const fe = create.error?.fieldErrors ?? {};

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("usersTitle")}
        description={t("usersDesc")}
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <Card
          bodyClass="p-0"
          title={t("accountsCard")}
          actions={
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                setPage(1);
                setSearch({ ...search, q });
              }}
            >
              <input
                aria-label={t("search")}
                className="input w-40 py-1"
                placeholder={t("search")}
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <select
                aria-label={t("thRole")}
                className="input w-auto py-1"
                value={search.role}
                onChange={(e) => {
                  setPage(1);
                  setSearch({ ...search, role: e.target.value as Role | "" });
                }}
              >
                <option value="">{t("allRoles")}</option>
                {(Object.keys(ROLE_KEYS) as Role[]).map((r) => (
                  <option key={r} value={r}>
                    {t(ROLE_KEYS[r])}
                  </option>
                ))}
              </select>
            </form>
          }
        >
          <ErrorAlert error={toggle.error} />
          {list.loading && !list.data ? (
            <div className="px-5 py-6">
              <Spinner label={t("loading")} />
            </div>
          ) : list.error ? (
            <div className="p-5">
              <ErrorAlert error={list.error} onRetry={list.reload} />
            </div>
          ) : list.data!.items.length === 0 ? (
            <EmptyState title={t("noData")} />
          ) : (
            <div className="overflow-x-auto">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>{t("thName")}</th>
                    <th>{t("thId")}</th>
                    <th>{t("thRole")}</th>
                    <th>{t("thSince")}</th>
                    <th>{t("thStatus")}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {list.data!.items.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <p className="font-medium text-ink">{u.full_name}</p>
                        <p className="text-xs text-muted">{u.email}</p>
                      </td>
                      <td className="code-text font-bold text-primary-700">{u.institutional_id}</td>
                      <td>{t(ROLE_KEYS[u.role])}</td>
                      <td>{formatDate(u.created_at)}</td>
                      <td>
                        {u.is_active ? (
                          <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            {t("active")}
                          </span>
                        ) : (
                          <span className="text-xs font-semibold text-muted bg-gray-100 px-2 py-0.5 rounded">
                            {t("closed")}
                          </span>
                        )}
                      </td>
                      <td className="text-right">
                        {u.id !== me.id && (
                          <Button
                            variant={u.is_active ? "danger" : "secondary"}
                            className="py-1"
                            onClick={async () => {
                              if (await toggle.run(u)) void list.reload();
                            }}
                          >
                            {u.is_active ? t("deactivate") : t("reactivate")}
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

        <Card title={t("addUserCard")}>
          <form className="space-y-3" onSubmit={onCreate} noValidate>
            {created && <Alert tone="success">Created {created.full_name} ({created.institutional_id}).</Alert>}
            <ErrorAlert error={create.error} />
            <Field label={t("signupIdLabel")} htmlFor="iid" error={fe.institutional_id}>
              <input
                id="iid"
                className="input uppercase"
                value={form.institutional_id}
                onChange={(e) => setForm({ ...form, institutional_id: e.target.value })}
              />
            </Field>
            <Field label={t("signupFullNameLabel")} htmlFor="name" error={fe.full_name}>
              <input
                id="name"
                className="input"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </Field>
            <Field label={t("signupEmailLabel")} htmlFor="email" error={fe.email}>
              <input
                id="email"
                type="email"
                className="input"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </Field>
            <Field label={t("signupPhoneLabel")} htmlFor="phone" error={fe.phone}>
              <input
                id="phone"
                className="input"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </Field>
            <Field label={t("thRole")} htmlFor="role">
              <select id="role" className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
                {(Object.keys(ROLE_KEYS) as Role[]).map((r) => (
                  <option key={r} value={r}>
                    {t(ROLE_KEYS[r])}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t("signupPasswordLabel")} htmlFor="pw" error={fe.password} hint={t("signupPasswordHint")}>
              <input
                id="pw"
                type="password"
                autoComplete="new-password"
                className="input"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </Field>
            <Button type="submit" pending={create.pending}>
              {t("addUserCard")}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
