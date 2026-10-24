import { useEffect, useState } from "react";
import { usersApi } from "../api/endpoints";
import type { UserBrief } from "../api/types";
import { useLanguage } from "../i18n/LanguageContext";

/** Type-ahead search for a learner by institutional ID, name, email or phone. */
export function LearnerPicker({
  id,
  value,
  onChange,
  error,
}: {
  id: string;
  value: UserBrief | null;
  onChange: (u: UserBrief | null) => void;
  error?: string;
}) {
  const { t } = useLanguage();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserBrief[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (value || query.trim().length < 2) {
      setResults([]);
      return;
    }
    const handle = setTimeout(() => {
      setSearching(true);
      usersApi
        .searchLearners(query.trim())
        .then(setResults)
        .catch(() => setResults([]))
        .finally(() => setSearching(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [query, value]);

  if (value) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-primary-200 bg-primary-50 px-3.5 py-2 text-sm">
        <span>
          <strong className="text-ink">{value.full_name}</strong>{" "}
          <span className="text-muted font-mono">({value.institutional_id})</span>
        </span>
        <button
          type="button"
          className="font-semibold text-primary-700 hover:text-primary-800 hover:underline"
          onClick={() => {
            onChange(null);
            setQuery("");
          }}
        >
          {t("change")}
        </button>
      </div>
    );
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      if (results.length > 0) {
        const exact =
          results.find((r) => r.institutional_id.toLowerCase() === query.trim().toLowerCase()) || results[0];
        onChange(exact);
      }
    }
  }

  return (
    <div className="relative">
      <input
        id={id}
        className="input"
        placeholder={t("learnerSearchPlaceholder")}
        value={query}
        autoComplete="off"
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        onKeyDown={handleKeyDown}
        onChange={(e) => setQuery(e.target.value)}
      />
      {(results.length > 0 || (searching && query.length >= 2)) && (
        <ul
          className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-line bg-white py-1 shadow-lg"
          role="listbox"
        >
          {searching && <li className="px-3 py-2 text-sm text-muted">{t("searching")}</li>}
          {results.map((u) => (
            <li key={u.id}>
              <button
                type="button"
                role="option"
                aria-selected="false"
                className="w-full px-3 py-2 text-left text-sm hover:bg-primary-50 hover:text-primary-800 transition flex justify-between items-center"
                onClick={() => onChange(u)}
              >
                <span>
                  <strong>{u.full_name}</strong> <span className="text-muted">({u.institutional_id})</span>
                </span>
                <span className="text-xs bg-surface-alt border border-primary-200 text-primary-700 px-2 py-0.5 rounded font-semibold">
                  {t("select")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {!searching && query.trim().length >= 2 && results.length === 0 && (
        <div className="mt-2 rounded-lg border border-line bg-surface-alt p-3 text-xs">
          <p className="text-muted">
            {t("noMatchingLearner")} “{query.trim()}”.
          </p>
          <button
            type="button"
            className="mt-1.5 font-semibold text-primary-700 hover:text-primary-800 hover:underline block text-left"
            onClick={() => {
              const cleaned = query.trim();
              const words = cleaned.split(/[\s,]+/);
              const numMatch = cleaned.match(/\d+/);
              const idCandidate = numMatch ? numMatch[0] : words[words.length - 1];
              const nameCandidate = cleaned.replace(idCandidate, "").replace(/[(),-]/g, "").trim() || cleaned;
              onChange({
                id: 0,
                institutional_id: idCandidate.toUpperCase(),
                full_name: nameCandidate,
              });
            }}
          >
            + {t("regPageTitle")} “{query.trim()}”
          </button>
        </div>
      )}
    </div>
  );
}
