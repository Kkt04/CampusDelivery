import { useNavigate } from "react-router-dom";
import type { Package } from "../api/types";
import { useLanguage } from "../i18n/LanguageContext";
import { formatDateTime } from "../lib/format";
import { OverdueFlag, StatusBadge } from "./StatusBadge";

/** Staff package table. Rows open the package; on small screens the table scrolls sideways. */
export function PackageTable({ packages, basePath }: { packages: Package[]; basePath: string }) {
  const navigate = useNavigate();
  const { t } = useLanguage();

  return (
    <div>
      {/* Mobile & 7-inch tablet card list (< md) */}
      <div className="md:hidden divide-y divide-line">
        {packages.map((p) => (
          <div
            key={p.id}
            onClick={() => navigate(`${basePath}/${p.id}`)}
            className="p-3.5 hover:bg-paper/70 active:bg-paper cursor-pointer space-y-2 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="code-text font-bold text-primary-700 text-sm">
                  {p.internal_code}
                </span>
                <span className="ml-2 text-xs font-medium text-muted">
                  {p.courier_name}
                </span>
                <div className="text-xs text-muted font-mono">{p.tracking_id ?? t("noTrackingId")}</div>
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <StatusBadge status={p.status} />
                {p.is_overdue && <OverdueFlag />}
              </div>
            </div>

            <div className="flex items-center justify-between text-xs pt-1 border-t border-line/40">
              <div className="text-ink font-medium">
                {p.recipient ? (
                  <span>
                    {p.recipient.full_name}{" "}
                    <span className="text-muted">({p.recipient.institutional_id})</span>
                  </span>
                ) : (
                  <span className="text-primary-700">{p.recipient_hint ?? t("unknownRecipientText")}</span>
                )}
              </div>
              <div className="text-right">
                <span className="text-muted mr-1">{t("thShelf")}:</span>
                <span className="code-text font-bold text-primary-800 bg-surface-alt px-1.5 py-0.5 rounded border border-line">
                  {p.storage_location?.code ?? "–"}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Desktop & Larger Tablet Table (>= md) */}
      <div className="hidden md:block overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th>{t("thPackage")}</th>
              <th>{t("thRecipient")}</th>
              <th>{t("thCourier")}</th>
              <th>{t("thArrived")}</th>
              <th>{t("thShelf")}</th>
              <th>{t("thStatus")}</th>
            </tr>
          </thead>
          <tbody>
            {packages.map((p) => (
              <tr key={p.id} className="cursor-pointer hover:bg-paper/70" onClick={() => navigate(`${basePath}/${p.id}`)}>
                <td>
                  <a
                    href={`${basePath}/${p.id}`}
                    className="code-text font-bold text-primary-700 hover:underline"
                    onClick={(e) => {
                      e.preventDefault();
                      navigate(`${basePath}/${p.id}`);
                    }}
                  >
                    {p.internal_code}
                  </a>
                  <div className="text-xs text-muted">{p.tracking_id ?? t("noTrackingId")}</div>
                </td>
                <td>
                  {p.recipient ? (
                    <>
                      <div className="font-medium text-ink">{p.recipient.full_name}</div>
                      <div className="text-xs text-muted">{p.recipient.institutional_id}</div>
                    </>
                  ) : (
                    <span className="text-primary-700 font-medium">{p.recipient_hint ?? t("unknownRecipientText")}</span>
                  )}
                </td>
                <td>{p.courier_name}</td>
                <td className="whitespace-nowrap">{formatDateTime(p.arrived_at)}</td>
                <td className="code-text font-medium text-primary-800">{p.storage_location?.code ?? "–"}</td>
                <td>
                  <div className="flex flex-wrap gap-1.5">
                    <StatusBadge status={p.status} />
                    {p.is_overdue && <OverdueFlag />}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
