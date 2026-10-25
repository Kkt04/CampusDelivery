import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { notificationsApi } from "../api/endpoints";
import type { Role } from "../api/types";
import { HOME_BY_ROLE, useAuth, useUser } from "../auth/AuthContext";
import { LanguageToggle, useLanguage } from "../i18n/LanguageContext";
import type { TranslationDictionary } from "../i18n/types";

interface NavConfigItem {
  to: string;
  labelKey: keyof TranslationDictionary;
  end?: boolean;
}

const NAV_CONFIG: Record<Role, NavConfigItem[]> = {
  LEARNER: [
    { to: "/learner", labelKey: "navOverview", end: true },
    { to: "/learner/packages", labelKey: "navMyPackages" },
    { to: "/learner/returns", labelKey: "navReturnParcel" },
    { to: "/learner/history", labelKey: "navPickupHistory" },
    { to: "/notifications", labelKey: "navNotifications" },
  ],
  SECURITY: [
    { to: "/security", labelKey: "navGateDashboard", end: true },
    { to: "/security/register", labelKey: "navRegisterPackage" },
    { to: "/security/packages", labelKey: "navIncomingPackages" },
    { to: "/security/pickup", labelKey: "navPickupHandover" },
    { to: "/security/incidents", labelKey: "navIncidents" },
    { to: "/notifications", labelKey: "navNotifications" },
  ],
  ADMIN: [
    { to: "/ops", labelKey: "navOpsOverview", end: true },
    { to: "/ops/packages", labelKey: "navPackages" },
    { to: "/ops/exceptions", labelKey: "navNeedsAttention" },
    { to: "/ops/storage", labelKey: "navStorage" },
    { to: "/ops/incidents", labelKey: "navIncidents" },
    { to: "/ops/users", labelKey: "navUsers" },
    { to: "/ops/audit", labelKey: "navAuditLog" },
  ],
};

const ROLE_KEYS: Record<Role, keyof TranslationDictionary> = {
  LEARNER: "roleLearner",
  SECURITY: "roleSecurity",
  ADMIN: "roleAdmin",
};

export function Layout() {
  const user = useUser();
  const { logout } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);

  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    notificationsApi.unreadCount().then((r) => setUnread(r.unread)).catch(() => setUnread(0));
  }, [location.pathname]);

  function handleSignOut() {
    logout();
    navigate("/login");
  }

  const nav = (
    <nav className="flex flex-col gap-1" aria-label="Main">
      {NAV_CONFIG[user.role].map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            `flex items-center justify-between rounded-lg px-3.5 py-2.5 text-sm font-medium transition-all ${
              isActive
                ? "bg-brand-soft text-brand-strong font-semibold shadow-2xs border-l-3 border-brand"
                : "text-ink hover:bg-surface-alt hover:text-brand"
            }`
          }
        >
          {t(item.labelKey)}
          {item.to === "/notifications" && unread > 0 && (
            <span
              className="rounded-full bg-brand px-2 py-0.5 text-xs font-semibold text-white shadow-2xs"
              aria-label={`${unread} unread`}
            >
              {unread}
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-surface-alt/40 flex flex-col">
      {/* Fixed Sticky Header across all screens */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-white/95 px-4 sm:px-6 py-2.5 shadow-2xs backdrop-blur-xs">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="rounded-lg border border-line p-2 text-ink hover:bg-surface-alt transition-colors lg:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? t("navClose") : t("navMenu")}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {open ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
          <Link to={HOME_BY_ROLE[user.role]} className="focus:outline-none">
            <Brand />
          </Link>
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          <LanguageToggle />

          <div className="hidden md:flex flex-col text-right leading-tight border-r border-line pr-3">
            <span className="text-sm font-semibold text-ink">{user.full_name}</span>
            <span className="text-xs text-muted">
              {user.institutional_id} • {t(ROLE_KEYS[user.role])}
            </span>
          </div>

          {/* Fixed, Always-Accessible Sign-Out Button */}
          <button
            type="button"
            onClick={handleSignOut}
            className="inline-flex items-center gap-1.5 rounded-lg border border-brand/20 bg-brand-soft px-3 py-1.5 text-xs sm:text-sm font-semibold text-brand hover:bg-brand hover:text-white transition-all active:scale-95 shadow-2xs"
            title={t("navSignOut")}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span className="hidden sm:inline">{t("navSignOut")}</span>
          </button>
        </div>
      </header>

      {/* Mobile navigation dropdown */}
      {open && (
        <div id="mobile-nav" className="border-b border-line bg-white px-4 pb-4 pt-2 shadow-sm lg:hidden">
          {nav}
          <div className="mt-4 border-t border-line pt-3 flex items-center justify-between">
            <div className="text-xs text-muted">
              <span className="font-semibold text-ink">{user.full_name}</span> ({user.institutional_id})
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              className="text-xs font-semibold text-brand hover:underline"
            >
              {t("navSignOut")}
            </button>
          </div>
        </div>
      )}

      {/* Main Layout Area */}
      <div className="flex-1 lg:grid lg:grid-cols-[256px_1fr]">
        <aside className="hidden border-r border-line bg-white lg:flex lg:flex-col lg:p-5 sticky top-[57px] h-[calc(100vh-57px)] overflow-y-auto shadow-2xs">
          <div className="flex-1">{nav}</div>
          <div className="border-t border-line pt-4 text-xs text-muted">
            <p className="font-semibold text-ink">{user.full_name}</p>
            <p className="mt-0.5">{user.institutional_id}</p>
            <p className="mt-0.5 text-brand font-medium">{t(ROLE_KEYS[user.role])}</p>
          </div>
        </aside>

        <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function Brand({ subtitle }: { subtitle?: string }) {
  const { t } = useLanguage();
  return (
    <div className="flex items-center gap-2.5">
      <img
        src="/logo.png"
        alt="Campus Delivery Logo"
        className="h-8 w-8 shrink-0 object-contain drop-shadow-xs"
      />
      <div className="leading-tight">
        <p className="text-base font-bold tracking-tight text-ink">{t("appTitle")}</p>
        <p className="text-xs text-muted">{subtitle ?? t("brandSubtitle")}</p>
      </div>
    </div>
  );
}
