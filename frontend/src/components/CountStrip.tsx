import { Link } from "react-router-dom";

export interface CountItem { label: string; value: number | string; to?: string; tone?: "warn" | "danger" | "brand" }

/** A single bordered row of counts. Linked counts open the matching filtered list. */
export function CountStrip({ items }: { items: CountItem[] }) {
  const tone = { warn: "text-warn", danger: "text-danger", brand: "text-brand-strong" };
  return (
    <div className="card grid grid-cols-2 divide-line overflow-hidden sm:grid-cols-3 lg:auto-cols-fr lg:grid-flow-col lg:grid-cols-none lg:divide-x">
      {items.map((item) => {
        const body = (
          <>
            <p className={`text-2xl font-bold ${item.tone && Number(item.value) > 0 ? tone[item.tone] : ""}`}>{item.value}</p>
            <p className="mt-0.5 text-sm text-muted">{item.label}</p>
          </>
        );
        return item.to ? (
          <Link key={item.label} to={item.to} className="border-b border-line px-5 py-4 hover:bg-paper/70 lg:border-b-0">{body}</Link>
        ) : (
          <div key={item.label} className="border-b border-line px-5 py-4 lg:border-b-0">{body}</div>
        );
      })}
    </div>
  );
}
