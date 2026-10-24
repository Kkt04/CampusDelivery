import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../../api/client";
import { authApi } from "../../api/endpoints";
import { HOME_BY_ROLE, useAuth } from "../../auth/AuthContext";
import { Brand } from "../../components/Layout";
import { Alert, Button, Field } from "../../components/ui";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // Forgot password modal state
  const [showForgot, setShowForgot] = useState(false);
  const [resetIdentifier, setResetIdentifier] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [forgotPending, setForgotPending] = useState(false);
  const [forgotError, setForgotError] = useState<string | null>(null);
  const [forgotSuccess, setForgotSuccess] = useState<string | null>(null);

  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const signedIn = await login(identifier.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from.startsWith(HOME_BY_ROLE[signedIn.role]) ? from : HOME_BY_ROLE[signedIn.role], { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Sign-in failed.");
    } finally {
      setPending(false);
    }
  }

  async function onResetSubmit(event: FormEvent) {
    event.preventDefault();
    setForgotError(null);
    setForgotSuccess(null);

    if (newPassword.length < 8) {
      setForgotError("Password must be at least 8 characters long.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setForgotError("Passwords do not match.");
      return;
    }

    setForgotPending(true);
    try {
      await authApi.resetPassword(resetIdentifier.trim(), newPassword);
      setForgotSuccess("Password reset successfully! Signing you in...");
      // Auto login with the newly set password
      const signedIn = await login(resetIdentifier.trim(), newPassword);
      setShowForgot(false);
      navigate(HOME_BY_ROLE[signedIn.role], { replace: true });
    } catch (e) {
      setForgotError(e instanceof ApiError ? e.message : "Password reset failed.");
    } finally {
      setForgotPending(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12">
        <div className="mx-auto w-full max-w-sm">
          <Brand />
          <h1 className="mt-10 text-2xl font-bold tracking-tight">Sign in</h1>
          <p className="mt-1 text-sm text-muted">Use your institutional ID or campus email.</p>
          <form className="mt-8 space-y-4" onSubmit={onSubmit} noValidate>
            {error && <Alert>{error}</Alert>}
            <Field label="Institutional ID or email" htmlFor="identifier">
              <input
                id="identifier"
                className="input"
                autoComplete="username"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="e.g. LRN-1001"
              />
            </Field>

            <div>
              <div className="flex items-center justify-between">
                <label className="label mb-0" htmlFor="password">Password</label>
                <button
                  type="button"
                  onClick={() => {
                    setResetIdentifier(identifier);
                    setNewPassword("");
                    setConfirmPassword("");
                    setForgotError(null);
                    setForgotSuccess(null);
                    setShowForgot(true);
                  }}
                  className="text-xs font-semibold text-brand hover:underline"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative mt-1">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  className="input pr-10"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted hover:text-ink focus:outline-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                    </svg>
                  ) : (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <Button type="submit" className="w-full" pending={pending} disabled={!identifier || !password}>
              Sign in
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-muted">
            New here?{" "}
            <Link to="/signup" className="font-semibold text-brand hover:underline">
              Create an account
            </Link>
          </p>

          {import.meta.env.DEV && (
            <div className="mt-8 rounded-md border border-line bg-white p-4 text-xs text-muted shadow-sm">
              <div className="font-semibold text-ink">Local testing accounts</div>
              <p className="mt-1">Click any account below to auto-fill credentials:</p>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  className="flex-1 rounded border border-line bg-surface-alt px-2.5 py-1.5 font-medium text-ink hover:bg-slate-100 transition active:scale-95 text-center"
                  onClick={() => {
                    setIdentifier("LRN-1001");
                    setPassword("Learner@123");
                    setError(null);
                  }}
                >
                  🧑‍🎓 <strong>Learner</strong><br />LRN-1001
                </button>
                <button
                  type="button"
                  className="flex-1 rounded border border-line bg-surface-alt px-2.5 py-1.5 font-medium text-ink hover:bg-slate-100 transition active:scale-95 text-center"
                  onClick={() => {
                    setIdentifier("SEC-001");
                    setPassword("Security@123");
                    setError(null);
                  }}
                >
                  👮 <strong>Security</strong><br />SEC-001
                </button>
                <button
                  type="button"
                  className="flex-1 rounded border border-line bg-surface-alt px-2.5 py-1.5 font-medium text-ink hover:bg-slate-100 transition active:scale-95 text-center"
                  onClick={() => {
                    setIdentifier("ADM-001");
                    setPassword("Admin@12345");
                    setError(null);
                  }}
                >
                  👨‍💼 <strong>Admin</strong><br />ADM-001
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="hidden flex-col justify-between bg-brand p-12 text-white lg:flex">
        <div className="flex flex-1 items-center justify-center py-6">
          <img
            src="/delivery-hero.png"
            alt="Campus Delivery Courier"
            className="max-h-[380px] w-auto max-w-full object-contain drop-shadow-xl"
          />
        </div>
        <div>
          <p className="max-w-md text-3xl font-bold leading-tight">
            Every parcel at Gate No. 2, from the courier’s hand to yours.
          </p>
          <p className="mt-4 max-w-md text-brand-soft/90">
            Security logs each arrival and shelf. You get notified, request a one-time code, and collect with your ID.
          </p>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div>
                <h2 className="text-lg font-bold text-ink">Reset Password</h2>
                <p className="text-xs text-muted mt-0.5">Enter your institutional ID or email to set a new password.</p>
              </div>
              <button
                type="button"
                onClick={() => setShowForgot(false)}
                className="rounded p-1 text-muted hover:bg-slate-100 hover:text-ink text-sm font-semibold"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <form onSubmit={onResetSubmit} className="mt-4 space-y-4">
              {forgotError && <Alert tone="danger">{forgotError}</Alert>}
              {forgotSuccess && <Alert tone="success">{forgotSuccess}</Alert>}

              <div>
                <label className="label" htmlFor="reset-identifier">Institutional ID or email</label>
                <input
                  id="reset-identifier"
                  type="text"
                  className="input"
                  required
                  placeholder="e.g. LRN-1001 or student@univ.edu"
                  value={resetIdentifier}
                  onChange={(e) => setResetIdentifier(e.target.value)}
                />
              </div>

              <div>
                <label className="label" htmlFor="new-password">New password</label>
                <div className="relative">
                  <input
                    id="new-password"
                    type={showNewPassword ? "text" : "password"}
                    className="input pr-10"
                    required
                    placeholder="Minimum 8 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-muted hover:text-ink focus:outline-none"
                    aria-label={showNewPassword ? "Hide password" : "Show password"}
                  >
                    {showNewPassword ? (
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                      </svg>
                    ) : (
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
                <p className="mt-1 text-xs text-muted">Must be at least 8 characters long.</p>
              </div>

              <div>
                <label className="label" htmlFor="confirm-password">Confirm new password</label>
                <input
                  id="confirm-password"
                  type={showNewPassword ? "text" : "password"}
                  className="input"
                  required
                  placeholder="Re-enter new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>

              <div className="mt-6 flex justify-end gap-3 pt-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setShowForgot(false)}
                  disabled={forgotPending}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  pending={forgotPending}
                  disabled={!resetIdentifier || !newPassword || !confirmPassword}
                >
                  Reset & sign in
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
