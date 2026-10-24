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
  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      if (results.length > 0) {
        const exact = results.find((r) => r.institutional_id.toLowerCase() === query.trim().toLowerCase()) || results[0];
        onChange(exact);
      }
    }
  }

  return (
    <div className="relative">
      <input id={id} className="input" placeholder="Search learner ID (e.g. 230136), name, or email" value={query} autoComplete="off"
        aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined}
        onKeyDown={handleKeyDown}
        onChange={(e) => setQuery(e.target.value)} />
      {(results.length > 0 || (searching && query.length >= 2)) && (
        <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-line bg-white py-1 shadow-md" role="listbox">
          {searching && <li className="px-3 py-2 text-sm text-muted">Searching…</li>}
          {results.map((u) => (
            <li key={u.id}>
              <button type="button" role="option" aria-selected="false"
                className="w-full px-3 py-2 text-left text-sm hover:bg-brand-soft hover:text-brand-strong transition flex justify-between items-center"
                onClick={() => onChange(u)}>
                <span><strong>{u.full_name}</strong> <span className="text-muted">({u.institutional_id})</span></span>
                <span className="text-xs bg-slate-100 text-ink px-2 py-0.5 rounded font-semibold">Select</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {!searching && query.trim().length >= 2 && results.length === 0 && (
        <div className="mt-2 rounded-md border border-line bg-surface-alt p-3 text-xs">
          <p className="text-muted">No registered account matches “{query.trim()}”.</p>
          <button
            type="button"
            className="mt-1.5 font-semibold text-brand hover:underline block text-left"
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
            + Register package for Enrollment ID “{query.trim()}” (auto-claims when student logs in)
          </button>
        </div>
      )}
    </div>
  );
}
