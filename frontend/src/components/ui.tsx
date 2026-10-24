import { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";

type Variant = "primary" | "secondary" | "danger" | "ghost";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-strong active:scale-[0.99] shadow-sm disabled:bg-brand/50 disabled:shadow-none transition-all",
  secondary: "bg-white text-ink border border-line hover:bg-surface-alt hover:border-brand/30 active:scale-[0.99] disabled:text-muted transition-all",
  danger: "bg-white text-danger border border-danger/30 hover:bg-danger-soft active:scale-[0.99] disabled:opacity-60 transition-all",
  ghost: "text-brand hover:bg-brand-soft hover:text-brand-strong active:scale-[0.99] disabled:text-muted transition-all",
};

export function Button({ variant = "primary", pending, children, className = "", ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; pending?: boolean }) {
  return (
    <button
      {...rest}
      disabled={rest.disabled || pending}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
    >
      {pending && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />}
      {children}
    </button>
  );
}

import { useLanguage } from "../i18n/LanguageContext";

export function Spinner({ label }: { label?: string }) {
  const { t } = useLanguage();
  return (
    <div className="flex items-center gap-3 py-8 text-sm text-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand border-t-transparent" aria-hidden />
      {label ?? t("loading")}…
    </div>
  );
}

export function Alert({ tone = "danger", title, children }: { tone?: "danger" | "success" | "info" | "warn"; title?: string; children?: ReactNode }) {
  const tones = {
    danger: "border-danger/30 bg-danger-soft text-danger",
    success: "border-brand/30 bg-brand-soft text-brand-strong",
    info: "border-done/20 bg-done-soft text-done",
    warn: "border-warn/30 bg-warn-soft text-warn",
  };
  return (
    <div className={`rounded-md border px-4 py-3 text-sm ${tones[tone]}`} role={tone === "danger" ? "alert" : "status"}>
      {title && <p className="font-semibold">{title}</p>}
      {children && <div className={title ? "mt-0.5" : ""}>{children}</div>}
    </div>
  );
}

export function ErrorAlert({ error, onRetry }: { error: ApiError | null; onRetry?: () => void }) {
  const { t } = useLanguage();
  if (!error) return null;
  return (
    <Alert tone="danger" title={error.message}>
      {onRetry && (
        <button className="mt-1 font-semibold underline underline-offset-2" onClick={onRetry}>
          {t("tryAgain")}
        </button>
      )}
    </Alert>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="px-6 py-12 text-center">
      <p className="font-semibold">{title}</p>
      {children && <p className="mx-auto mt-1 max-w-md text-sm text-muted">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, actions, children, className = "", bodyClass = "p-5" }:
  { title?: string; actions?: ReactNode; children: ReactNode; className?: string; bodyClass?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
          {title && <h2 className="text-sm font-semibold">{title}</h2>}
          {actions}
        </header>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

export function Field({ label, htmlFor, error, hint, children }:
  { label: string; htmlFor: string; error?: string; hint?: string; children: ReactNode }) {
  return (
    <div>
      <label className="label" htmlFor={htmlFor}>{label}</label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-muted">{hint}</p>}
      {error && <p className="mt-1 text-xs font-medium text-danger" id={`${htmlFor}-error`}>{error}</p>}
    </div>
  );
}

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const { t } = useLanguage();
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total === 0) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);
  return (
    <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm text-muted">
      <span>{from}–{to} {t("of")} {total}</span>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>{t("previous")}</Button>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>{t("next")}</Button>
      </div>
    </div>
  );
}

export function KeyValue({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
      {items.map(([k, v]) => (
        <div key={k}>
          <dt className="text-muted">{k}</dt>
          <dd className="mt-0.5 font-medium">{v ?? "–"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function TextLink({ to, children }: { to: string; children: ReactNode }) {
  return <Link to={to} className="font-semibold text-brand hover:text-brand-strong underline-offset-2 hover:underline transition-colors">{children}</Link>;
}
