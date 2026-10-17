import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../../api/client";
import { HOME_BY_ROLE, useAuth } from "../../auth/AuthContext";
import { Brand } from "../../components/Layout";
import { Alert, Button, Field } from "../../components/ui";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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
              <input id="identifier" className="input" autoComplete="username" required value={identifier}
                onChange={(e) => setIdentifier(e.target.value)} placeholder="e.g. LRN-1001" />
            </Field>
            <Field label="Password" htmlFor="password">
              <input id="password" type="password" className="input" autoComplete="current-password" required
                value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <Button type="submit" className="w-full" pending={pending} disabled={!identifier || !password}>Sign in</Button>
          </form>
          <p className="mt-6 text-center text-sm text-muted">
            New here?{" "}
            <Link to="/signup" className="font-semibold text-brand hover:underline">Create an account</Link>
          </p>
          {import.meta.env.DEV && (
            <details className="mt-8 rounded-md border border-line bg-white p-3 text-xs text-muted">
              <summary className="cursor-pointer font-semibold text-ink">Local testing accounts</summary>
              <p className="mt-2">Development seed data only. Never use these outside a local machine.</p>
              <ul className="mt-2 space-y-1">
                <li>Learner: LRN-1001 / Learner@123</li>
                <li>Security: SEC-001 / Security@123</li>
                <li>Operations: ADM-001 / Admin@12345</li>
              </ul>
            </details>
          )}
        </div>
      </div>
      <div className="hidden flex-col justify-end bg-brand p-12 text-white lg:flex">
        <p className="max-w-md text-3xl font-bold leading-tight">
          Every parcel at Gate No. 2, from the courier’s hand to yours.
        </p>
        <p className="mt-4 max-w-md text-brand-soft/90">
          Security logs each arrival and shelf. You get notified, request a one-time code, and collect with your ID.
        </p>
      </div>
    </div>
  );
}
