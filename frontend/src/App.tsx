import { Navigate, Route, Routes } from "react-router-dom";
import { HOME_BY_ROLE, useAuth } from "./auth/AuthContext";
import { RequireRole } from "./auth/RequireRole";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/ui";
import { LearnerDashboard } from "./pages/learner/LearnerDashboard";
import { MyPackages } from "./pages/learner/MyPackages";
import { PickupCodePage } from "./pages/learner/PickupCodePage";
import { PickupHistory } from "./pages/learner/PickupHistory";
import { OpsDashboard } from "./pages/ops/OpsDashboard";
import { AuditPage } from "./pages/ops/AuditPage";
import { ExceptionsPage } from "./pages/ops/ExceptionsPage";
import { IncidentsReview } from "./pages/ops/IncidentsReview";
import { StorageManagement } from "./pages/ops/StorageManagement";
import { UsersPage } from "./pages/ops/UsersPage";
import { IncidentReporting } from "./pages/security/IncidentReporting";
import { PickupVerification } from "./pages/security/PickupVerification";
import { RegisterPackage } from "./pages/security/RegisterPackage";
import { SecurityDashboard } from "./pages/security/SecurityDashboard";
import { LoginPage } from "./pages/shared/LoginPage";
import { SignupPage } from "./pages/shared/SignupPage";
import { NotFoundPage, UnauthorizedPage } from "./pages/shared/StatusPages";
import { NotificationsPage } from "./pages/shared/NotificationsPage";
import { PackageDetailPage } from "./pages/shared/PackageDetailPage";
import { PackagesListPage } from "./pages/shared/PackagesListPage";

function Home() {
  const { user, ready } = useAuth();
  if (!ready) return <Spinner />;
  return <Navigate to={user ? HOME_BY_ROLE[user.role] : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      <Route element={<RequireRole roles={["LEARNER", "SECURITY", "ADMIN"]} />}>
        <Route element={<Layout />}>
          <Route path="/notifications" element={<NotificationsPage />} />
        </Route>
      </Route>

      <Route element={<RequireRole roles={["LEARNER"]} />}>
        <Route element={<Layout />}>
          <Route path="/learner" element={<LearnerDashboard />} />
          <Route path="/learner/packages" element={<MyPackages />} />
          <Route path="/learner/packages/:id" element={<PackageDetailPage />} />
          <Route path="/learner/packages/:id/pickup" element={<PickupCodePage />} />
          <Route path="/learner/history" element={<PickupHistory />} />
        </Route>
      </Route>

      <Route element={<RequireRole roles={["SECURITY"]} />}>
        <Route element={<Layout />}>
          <Route path="/security" element={<SecurityDashboard />} />
          <Route path="/security/register" element={<RegisterPackage />} />
          <Route path="/security/packages" element={<PackagesListPage title="Incoming packages"
            description="Everything currently in custody at Gate No. 2. Open a package to assign storage or update it."
            basePath="/security/packages" defaultScope="custody" />} />
          <Route path="/security/packages/:id" element={<PackageDetailPage />} />
          <Route path="/security/pickup" element={<PickupVerification />} />
          <Route path="/security/incidents" element={<IncidentReporting />} />
        </Route>
      </Route>

      <Route element={<RequireRole roles={["ADMIN"]} />}>
        <Route element={<Layout />}>
          <Route path="/ops" element={<OpsDashboard />} />
          <Route path="/ops/packages" element={<PackagesListPage title="Packages"
            description="Search every package by code, tracking ID, courier or learner." basePath="/ops/packages" defaultScope="all" />} />
          <Route path="/ops/packages/:id" element={<PackageDetailPage />} />
          <Route path="/ops/exceptions" element={<ExceptionsPage />} />
          <Route path="/ops/storage" element={<StorageManagement />} />
          <Route path="/ops/incidents" element={<IncidentsReview />} />
          <Route path="/ops/users" element={<UsersPage />} />
          <Route path="/ops/audit" element={<AuditPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
