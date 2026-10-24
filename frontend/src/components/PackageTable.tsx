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
    <div className="overflow-x-auto">
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
  );
}
