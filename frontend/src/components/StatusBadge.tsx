import type { PackageStatus } from "../api/types";
import { STATUS_KEYS, STATUS_META, TONE_CLASSES } from "../lib/status";
import { useLanguage } from "../i18n/LanguageContext";

export function StatusBadge({ status, learner = false }: { status: PackageStatus; learner?: boolean }) {
  const { t } = useLanguage();
  const meta = STATUS_META[status];
  const keys = STATUS_KEYS[status];
  const label = keys ? t(learner ? keys.learnerKey : keys.labelKey) : (learner ? meta.learnerLabel : meta.label);

  return (
    <span className={`inline-flex whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold ${TONE_CLASSES[meta.tone]}`}>
      {label}
    </span>
  );
}

export function OverdueFlag() {
  const { t } = useLanguage();
  return (
    <span className="inline-flex whitespace-nowrap rounded-full border border-warn/30 px-2 py-0.5 text-xs font-semibold text-warn"
      title="Waiting longer than the collection deadline">
      {t("overdue")}
    </span>
  );
}
