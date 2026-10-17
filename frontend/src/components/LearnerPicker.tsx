import { useEffect, useState } from "react";
import { usersApi } from "../api/endpoints";
import type { UserBrief } from "../api/types";

/** Type-ahead search for a learner by institutional ID, name, email or phone. */
export function LearnerPicker({ id, value, onChange, error }:
  { id: string; value: UserBrief | null; onChange: (u: UserBrief | null) => void; error?: string }) {
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
      usersApi.searchLearners(query.trim()).then(setResults).catch(() => setResults([])).finally(() => setSearching(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [query, value]);

  if (value) {
    return (
      <div className="flex items-center justify-between rounded-md border border-brand/30 bg-brand-soft px-3 py-2 text-sm">
        <span><strong>{value.full_name}</strong> <span className="text-muted">({value.institutional_id})</span></span>
        <button type="button" className="font-semibold text-brand-strong hover:underline" onClick={() => { onChange(null); setQuery(""); }}>
          Change
        </button>
      </div>
    );
  }
  return (
    <div className="relative">
      <input id={id} className="input" placeholder="Search learner ID, name, email or phone" value={query} autoComplete="off"
        aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined}
        onChange={(e) => setQuery(e.target.value)} />
      {(results.length > 0 || (searching && query.length >= 2)) && (
        <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-line bg-white py-1 shadow-sm" role="listbox">
          {searching && <li className="px-3 py-2 text-sm text-muted">Searching…</li>}
          {results.map((u) => (
            <li key={u.id}>
              <button type="button" role="option" aria-selected="false"
                className="w-full px-3 py-2 text-left text-sm hover:bg-paper" onClick={() => onChange(u)}>
                <strong>{u.full_name}</strong> <span className="text-muted">{u.institutional_id}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {!searching && query.trim().length >= 2 && results.length === 0 && (
        <p className="mt-1 text-xs text-muted">No active learner matches “{query.trim()}”.</p>
      )}
    </div>
  );
}
