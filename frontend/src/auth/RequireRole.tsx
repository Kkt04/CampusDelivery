import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Role } from "../api/types";
import { Spinner } from "../components/ui";
import { useAuth } from "./AuthContext";

/** UX guard only. The backend independently enforces every permission. */
export function RequireRole({ roles }: { roles: Role[] }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <div className="grid min-h-screen place-items-center"><Spinner label="Loading your session" /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!roles.includes(user.role)) return <Navigate to="/unauthorized" replace />;
  return <Outlet />;
}
