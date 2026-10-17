import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { notificationsApi } from "../api/endpoints";
import type { Role } from "../api/types";
import { useAuth, useUser } from "../auth/AuthContext";

interface NavItem { to: string; label: string; end?: boolean }

const NAV: Record<Role, NavItem[]> = {
  LEARNER: [
    { to: "/learner", label: "Overview", end: true },
    { to: "/learner/packages", label: "My packages" },
    { to: "/learner/history", label: "Pickup history" },
    { to: "/notifications", label: "Notifications" },
  ],
  SECURITY: [
    { to: "/security", label: "Gate dashboard", end: true },
    { to: "/security/register", label: "Register package" },
    { to: "/security/packages", label: "Incoming packages" },
    { to: "/security/pickup", label: "Pickup handover" },
    { to: "/security/incidents", label: "Incidents" },
    { to: "/notifications", label: "Notifications" },
  ],
  ADMIN: [
    { to: "/ops", label: "Operations overview", end: true },
    { to: "/ops/packages", label: "Packages" },
    { to: "/ops/exceptions", label: "Needs attention" },
    { to: "/ops/storage", label: "Storage" },
    { to: "/ops/incidents", label: "Incidents" },
    { to: "/ops/users", label: "Users" },
    { to: "/ops/audit", label: "Audit log" },
  ],
};

const ROLE_NAME: Record<Role, string> = { LEARNER: "Learner", SECURITY: "Gate No. 2 security", ADMIN: "Operations" };

export function Layout() {
  const user = useUser();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);

  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    notificationsApi.unreadCount().then((r) => setUnread(r.unread)).catch(() => setUnread(0));
  }, [location.pathname]);

  const nav = (
    <nav className="flex flex-col gap-0.5" aria-label="Main">
      {NAV[user.role].map((item) => (
        <NavLink key={item.to} to={item.to} end={item.end}
          className={({ isActive }) =>
            `flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium ${
              isActive ? "bg-brand-soft text-brand-strong" : "text-ink hover:bg-paper"}`}>
          {item.label}
          {item.to === "/notifications" && unread > 0 && (
            <span className="rounded-full bg-brand px-1.5 text-xs font-semibold text-white" aria-label={`${unread} unread`}>{unread}</span>
          )}
        </NavLink>
      ))}
    </nav>
  );

  const identity = (
    <div className="border-t border-line pt-4">
      <p className="text-sm font-semibold">{user.full_name}</p>
      <p className="text-xs text-muted">{user.institutional_id}, {ROLE_NAME[user.role]}</p>
      <button className="mt-3 text-sm font-semibold text-brand-strong hover:underline"
        onClick={() => { logout(); navigate("/login"); }}>
        Sign out
      </button>
    </div>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="hidden border-r border-line bg-white lg:flex lg:flex-col lg:justify-between lg:p-5">
        <div>
          <Brand />
          <div className="mt-6">{nav}</div>
        </div>
        {identity}
      </aside>

      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-line bg-white px-4 py-3 lg:hidden">
        <Brand />
        <button className="rounded-md border border-line px-3 py-1.5 text-sm font-semibold" aria-expanded={open}
          aria-controls="mobile-nav" onClick={() => setOpen((o) => !o)}>
          {open ? "Close" : "Menu"}
        </button>
      </header>
      {open && (
        <div id="mobile-nav" className="border-b border-line bg-white px-4 pb-4 pt-2 lg:hidden">
          {nav}
          <div className="mt-4">{identity}</div>
        </div>
      )}

      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
        <Outlet />
      </main>
    </div>
  );
}

export function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
        <rect width="32" height="32" rx="7" fill="#C2410C" />
        <path d="M8 12.5 16 8l8 4.5v8L16 25l-8-4.5zM8 12.5 16 17l8-4.5M16 17v8" fill="none" stroke="#fff" strokeWidth="2" strokeLinejoin="round" />
      </svg>
      <div className="leading-tight">
        <p className="text-sm font-bold">Campus Deliveries</p>
        <p className="text-xs text-muted">Gate No. 2</p>
      </div>
    </div>
  );
}
