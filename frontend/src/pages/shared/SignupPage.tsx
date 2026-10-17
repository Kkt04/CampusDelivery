import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../../api/client";
import { HOME_BY_ROLE, useAuth } from "../../auth/AuthContext";
import { Brand } from "../../components/Layout";
import { Alert, Button, Field } from "../../components/ui";

export function SignupPage() {
  const { user, signup } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [institutionalId, setInstitutionalId] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);

  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setPending(true);
    try {
      const user = await signup({
        institutional_id: institutionalId.trim(),
        full_name: fullName.trim(),
        email: email.trim(),
        phone: phone.trim() || null,
        password,
      });
      navigate(HOME_BY_ROLE[user.role], { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        const details = err.fieldErrors;
        setError(Object.keys(details).length ? "Please fix the highlighted fields." : err.message);
        setFieldErrors(details);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md rounded-lg border border-line bg-white p-8 shadow-sm">
        <Brand />
        <h1 className="mt-6 text-2xl font-bold text-ink">Create your account</h1>
        <p className="mt-1 text-sm text-muted">Learners can self-register. Staff accounts are issued by operations.</p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit} noValidate>
          {error && <Alert>{error}</Alert>}
          <Field label="Full name" htmlFor="full_name" error={fieldErrors.full_name}>
            <input id="full_name" className="input" autoComplete="name" required value={fullName}
              onChange={(e) => setFullName(e.target.value)} placeholder="e.g. Ada Lovelace" />
          </Field>
          <Field label="Institutional ID" htmlFor="institutional_id" error={fieldErrors.institutional_id}
            hint="Letters, numbers and hyphens, e.g. LRN-1042.">
            <input id="institutional_id" className="input" autoComplete="username" required value={institutionalId}
              onChange={(e) => setInstitutionalId(e.target.value)} placeholder="LRN-1042" />
          </Field>
          <Field label="Email" htmlFor="email" error={fieldErrors.email}>
            <input id="email" type="email" className="input" autoComplete="email" required value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="you@campus.example.edu" />
          </Field>
          <Field label="Phone (optional)" htmlFor="phone" error={fieldErrors.phone}>
            <input id="phone" className="input" autoComplete="tel" value={phone}
              onChange={(e) => setPhone(e.target.value)} placeholder="+1 555 0100" />
          </Field>
          <Field label="Password" htmlFor="password" error={fieldErrors.password}
            hint="At least 8 characters, mixing letters with numbers or symbols.">
            <input id="password" type="password" className="input" autoComplete="new-password" required value={password}
              onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Field label="Confirm password" htmlFor="confirm" error={confirm && password !== confirm ? "Passwords do not match." : undefined}>
            <input id="confirm" type="password" className="input" autoComplete="new-password" required value={confirm}
              onChange={(e) => setConfirm(e.target.value)} />
          </Field>
          <Button type="submit" className="w-full" pending={pending}
            disabled={!fullName || !institutionalId || !email || !password || !confirm || password !== confirm}>
            Create account
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-brand hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
