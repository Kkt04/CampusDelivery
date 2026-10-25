import { FormEvent, useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, tokenStore } from "../../api/client";
import { authApi } from "../../api/endpoints";
import { HOME_BY_ROLE, useAuth } from "../../auth/AuthContext";
import { Brand } from "../../components/Layout";
import { Alert, Button, Field } from "../../components/ui";
import { LanguageToggle, useLanguage } from "../../i18n/LanguageContext";

interface LoginPageProps {
  defaultMode?: "login" | "signup";
}

export function LoginPage({ defaultMode = "login" }: LoginPageProps) {
  const { user, login, signup } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  // Mode state: 'login' or 'signup'
  const initialMode = searchParams.get("mode") === "signup" ? "signup" : defaultMode;
  const [mode, setMode] = useState<"login" | "signup">(initialMode);

  // Sync mode with URL if needed
  useEffect(() => {
    if (searchParams.get("mode") === "signup") {
      setMode("signup");
    }
  }, [searchParams]);

  function switchMode(newMode: "login" | "signup") {
    setMode(newMode);
    setError(null);
    setFieldErrors({});
    if (newMode === "signup") {
      setSearchParams({ mode: "signup" });
    } else {
      setSearchParams({});
    }
  }

  // Login form state
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // Signup form state
  const [fullName, setFullName] = useState("");
  const [signupId, setSignupId] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPhone, setSignupPhone] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showSignupPassword, setShowSignupPassword] = useState(false);

  // Common UI state
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);

  // Forgot password modal state
  const [showForgot, setShowForgot] = useState(false);
  const [resetStep, setResetStep] = useState<1 | 2>(1);
  const [resetIdentifier, setResetIdentifier] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [devTokenHint, setDevTokenHint] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmResetPassword, setConfirmResetPassword] = useState("");
  const [forgotPending, setForgotPending] = useState(false);
  const [forgotError, setForgotError] = useState<string | null>(null);
  const [forgotSuccess, setForgotSuccess] = useState<string | null>(null);

  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />;

  async function onLoginSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const signedIn = await login(identifier.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from.startsWith(HOME_BY_ROLE[signedIn.role]) ? from : HOME_BY_ROLE[signedIn.role], {
        replace: true,
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("signInFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onSignupSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFieldErrors({});

    if (signupPassword !== confirmPassword) {
      setError(t("resetPasswordMismatch"));
      return;
    }
    if (signupPassword.length < 8) {
      setError(t("signupPasswordHint"));
      return;
    }

    setPending(true);
    try {
      const newUser = await signup({
        institutional_id: signupId.trim().toUpperCase(),
        full_name: fullName.trim(),
        email: signupEmail.trim(),
        phone: signupPhone.trim() || null,
        password: signupPassword,
      });
      navigate(HOME_BY_ROLE[newUser.role], { replace: true });
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

  async function onRequestTokenSubmit(event: FormEvent) {
    event.preventDefault();
    setForgotError(null);
    setForgotSuccess(null);
    setForgotPending(true);
    try {
      const res = await authApi.forgotPassword(resetIdentifier.trim());
      setForgotSuccess(res.message);
      if (res.dev_token) {
        setDevTokenHint(res.dev_token);
        setResetToken(res.dev_token);
      }
      setResetStep(2);
    } catch (e) {
      setForgotError(e instanceof ApiError ? e.message : "Failed to request reset token.");
    } finally {
      setForgotPending(false);
    }
  }

  async function onResetTokenSubmit(event: FormEvent) {
    event.preventDefault();
    setForgotError(null);
    setForgotSuccess(null);

    if (newPassword.length < 8) {
      setForgotError(t("resetMinLength"));
      return;
    }
    if (newPassword !== confirmResetPassword) {
      setForgotError(t("resetPasswordMismatch"));
      return;
    }

    setForgotPending(true);
    try {
      const result = await authApi.resetPasswordWithToken(resetToken.trim(), newPassword);
      tokenStore.set(result.access_token);
      if (result.refresh_token) {
        tokenStore.setRefreshToken(result.refresh_token);
      }
      setForgotSuccess("Password updated successfully! Logging you in...");
      setTimeout(() => {
        setShowForgot(false);
        navigate(HOME_BY_ROLE[result.user.role], { replace: true });
      }, 700);
    } catch (e) {
      setForgotError(e instanceof ApiError ? e.message : t("resetFailed"));
    } finally {
      setForgotPending(false);
    }
  }

  return (
    <div className="min-h-[100dvh] lg:h-[100dvh] lg:overflow-hidden bg-white lg:grid lg:grid-cols-12">
      {/* Mobile & Tablet Header (< lg) */}
      <div className="border-b border-line bg-surface-alt px-4 py-3 flex items-center justify-between lg:hidden shrink-0">
        <Brand />
        <LanguageToggle />
      </div>

      {/* Authentication Form Column */}
      <div className="flex flex-col justify-between px-6 py-6 sm:px-10 lg:col-span-5 lg:px-10 lg:py-7 xl:col-span-5 overflow-y-auto">
        <div className="hidden lg:flex items-center justify-between">
          <Brand />
          <LanguageToggle />
        </div>

        <div className="mx-auto w-full max-w-sm py-2">
          {/* In-Place Mode Switcher Tabs */}
          <div className="mb-5 flex rounded-xl border border-line bg-surface-alt p-1">
            <button
              type="button"
              className={`flex-1 rounded-lg py-2 text-xs sm:text-sm font-semibold transition-all ${
                mode === "login"
                  ? "bg-white text-primary-700 shadow-sm"
                  : "text-muted hover:text-ink"
              }`}
              onClick={() => switchMode("login")}
            >
              {t("authSignInBtn")}
            </button>
            <button
              type="button"
              className={`flex-1 rounded-lg py-2 text-xs sm:text-sm font-semibold transition-all ${
                mode === "signup"
                  ? "bg-white text-primary-700 shadow-sm"
                  : "text-muted hover:text-ink"
              }`}
              onClick={() => switchMode("signup")}
            >
              {t("landingCreateAccountBtn")}
            </button>
          </div>

          {/* Form Header */}
          <div className="mb-5">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink font-serif">
              {mode === "login" ? t("authSignInTitle") : t("signupTitle")}
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-muted">
              {mode === "login" ? t("authSignInSubtitle") : t("signupSubtitle")}
            </p>
          </div>

          {error && <div className="mb-4"><Alert tone="danger">{error}</Alert></div>}

          {/* SIGN IN FORM */}
          {mode === "login" && (
            <form className="space-y-3.5" onSubmit={onLoginSubmit} noValidate>
              <Field label={t("authIdentifierLabel")} htmlFor="identifier">
                <input
                  id="identifier"
                  className="input"
                  autoComplete="username"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder={t("authIdentifierPlaceholder")}
                />
              </Field>

              <div>
                <div className="flex items-center justify-between">
                  <label className="label mb-0" htmlFor="password">
                    {t("authPasswordLabel")}
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setResetIdentifier(identifier);
                      setNewPassword("");
                      setConfirmResetPassword("");
                      setForgotError(null);
                      setForgotSuccess(null);
                      setShowForgot(true);
                    }}
                    className="text-xs font-semibold text-primary-700 hover:text-primary-800 transition-colors hover:underline"
                  >
                    {t("authForgotPassword")}
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
                    aria-label={showPassword ? t("authHidePassword") : t("authShowPassword")}
                  >
                    {showPassword ? (
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                      </svg>
                    ) : (
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268-2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              <Button type="submit" className="w-full shadow-sm mt-1" pending={pending} disabled={!identifier || !password}>
                {t("authSignInBtn")}
              </Button>

              {import.meta.env.DEV && (
                <div className="mt-5 rounded-xl border border-line bg-surface-alt/70 p-3.5 text-xs text-muted shadow-2xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-ink">{t("authLocalTestAccounts")}</span>
                    <span className="rounded bg-primary-100 px-1.5 py-0.5 text-[10px] font-bold text-primary-800 uppercase tracking-wider">
                      {t("devMode")}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px]">{t("authClickToAutofill")}</p>
                  <div className="mt-2.5 flex flex-col gap-1.5 sm:flex-row">
                    <button
                      type="button"
                      className="flex-1 rounded-lg border border-line bg-white px-2 py-1.5 font-medium text-ink hover:border-primary-400 hover:bg-primary-50 transition-all active:scale-95 text-center shadow-2xs"
                      onClick={() => {
                        setIdentifier("LRN-1001");
                        setPassword("Learner@123");
                        setError(null);
                      }}
                    >
                      🧑‍🎓 <strong>{t("authLearner")}</strong><br />
                      <span className="text-[10px] text-muted">LRN-1001</span>
                    </button>
                    <button
                      type="button"
                      className="flex-1 rounded-lg border border-line bg-white px-2 py-1.5 font-medium text-ink hover:border-primary-400 hover:bg-primary-50 transition-all active:scale-95 text-center shadow-2xs"
                      onClick={() => {
                        setIdentifier("SEC-001");
                        setPassword("Security@123");
                        setError(null);
                      }}
                    >
                      👮 <strong>{t("authSecurity")}</strong><br />
                      <span className="text-[10px] text-muted">SEC-001</span>
                    </button>
                    <button
                      type="button"
                      className="flex-1 rounded-lg border border-line bg-white px-2 py-1.5 font-medium text-ink hover:border-primary-400 hover:bg-primary-50 transition-all active:scale-95 text-center shadow-2xs"
                      onClick={() => {
                        setIdentifier("ADM-001");
                        setPassword("Admin@12345");
                        setError(null);
                      }}
                    >
                      👨‍💼 <strong>{t("authAdmin")}</strong><br />
                      <span className="text-[10px] text-muted">ADM-001</span>
                    </button>
                  </div>
                </div>
              )}
            </form>
          )}

          {/* CREATE ACCOUNT (SIGNUP) FORM */}
          {mode === "signup" && (
            <form className="space-y-3" onSubmit={onSignupSubmit} noValidate>
              <Field label={t("signupFullNameLabel")} htmlFor="full_name" error={fieldErrors.full_name}>
                <input
                  id="full_name"
                  className="input"
                  autoComplete="name"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder={t("signupFullNamePlaceholder")}
                />
              </Field>

              <Field
                label={t("signupIdLabel")}
                htmlFor="signup_id"
                error={fieldErrors.institutional_id}
                hint={t("signupIdHint")}
              >
                <input
                  id="signup_id"
                  className="input uppercase"
                  autoComplete="username"
                  required
                  value={signupId}
                  onChange={(e) => setSignupId(e.target.value)}
                  placeholder={t("signupIdPlaceholder")}
                />
              </Field>

              <Field label={t("signupEmailLabel")} htmlFor="signup_email" error={fieldErrors.email}>
                <input
                  id="signup_email"
                  type="email"
                  className="input"
                  autoComplete="email"
                  required
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder={t("signupEmailPlaceholder")}
                />
              </Field>

              <Field label={t("signupPhoneLabel")} htmlFor="signup_phone" error={fieldErrors.phone}>
                <input
                  id="signup_phone"
                  type="tel"
                  className="input"
                  autoComplete="tel"
                  value={signupPhone}
                  onChange={(e) => setSignupPhone(e.target.value)}
                  placeholder={t("signupPhonePlaceholder")}
                />
              </Field>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Field label={t("signupPasswordLabel")} htmlFor="signup_password" error={fieldErrors.password}>
                  <div className="relative">
                    <input
                      id="signup_password"
                      type={showSignupPassword ? "text" : "password"}
                      className="input pr-8"
                      autoComplete="new-password"
                      required
                      value={signupPassword}
                      onChange={(e) => setSignupPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowSignupPassword(!showSignupPassword)}
                      className="absolute inset-y-0 right-0 flex items-center pr-2 text-muted hover:text-ink focus:outline-none"
                    >
                      <span className="text-xs">{showSignupPassword ? "🙈" : "👁️"}</span>
                    </button>
                  </div>
                </Field>

                <Field label={t("signupConfirmPasswordLabel")} htmlFor="confirm_password">
                  <input
                    id="confirm_password"
                    type={showSignupPassword ? "text" : "password"}
                    className="input"
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </Field>
              </div>

              <Button
                type="submit"
                className="w-full shadow-sm mt-2"
                pending={pending}
                disabled={!fullName.trim() || !signupId.trim() || !signupEmail.trim() || !signupPassword}
              >
                {t("signupSubmitBtn")}
              </Button>
            </form>
          )}
        </div>

        {/* Bottom whitespace spacer (no Gate No. 2 footer line as requested) */}
        <div className="h-2 shrink-0" />
      </div>

      {/* Desktop Hero Section (>= lg) with Red-Themed Background */}
      <div className="hidden border-l border-primary-900 bg-gradient-to-br from-[#C62828] via-[#E53935] to-[#8E1B1B] text-white p-8 lg:p-10 xl:p-12 lg:flex lg:col-span-7 xl:col-span-7 flex-col justify-center items-center overflow-hidden">
        <div className="mx-auto w-full max-w-lg text-center flex flex-col justify-center items-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/15 px-4 py-1.5 text-xs font-semibold text-white shadow-2xs mb-3">
            <span>📦</span>
            <span>{t("eyebrow")}</span>
          </div>

          <div className="my-3 flex items-center justify-center">
            <img
              src="/delivery-hero.png"
              alt="Campus delivery courier"
              className="max-h-[30dvh] lg:max-h-[34dvh] w-auto max-w-full object-contain drop-shadow-2xl transition-transform duration-300 hover:scale-[1.02]"
            />
          </div>

          <h2 className="text-2xl lg:text-3xl xl:text-4xl font-bold tracking-tight text-white font-serif leading-snug">
            {t("landingHeadingLine1")}<br />
            <span className="text-red-100">{t("landingHeadingLine2")}</span>
          </h2>

          <p className="mt-3 max-w-md text-xs lg:text-sm text-white/90 leading-relaxed font-normal">
            {t("landingDescription")}
          </p>

          <div className="mt-5 grid grid-cols-3 gap-3 w-full border-t border-white/20 pt-4 text-center">
            <div className="rounded-xl bg-white/10 border border-white/15 px-2 py-2 backdrop-blur-2xs">
              <div className="text-base lg:text-lg font-bold text-white font-serif">{t("landingCustodyLogged")}</div>
              <div className="text-[10px] text-white/80">{t("landingTrustCustody")}</div>
            </div>
            <div className="rounded-xl bg-white/10 border border-white/15 px-2 py-2 backdrop-blur-2xs">
              <div className="text-base lg:text-lg font-bold text-white font-serif">{t("landingArrivalAlerts")}</div>
              <div className="text-[10px] text-white/80">{t("landingTrustAlerts")}</div>
            </div>
            <div className="rounded-xl bg-white/10 border border-white/15 px-2 py-2 backdrop-blur-2xs">
              <div className="text-base lg:text-lg font-bold text-white font-serif">{t("landingOtpHandover")}</div>
              <div className="text-[10px] text-white/80">{t("landingTrustHandover")}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-line bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div>
                <h2 className="text-lg font-bold text-ink font-serif">{t("authForgotPassword")}</h2>
                <p className="text-xs text-muted">
                  {resetStep === 1 ? "Step 1 of 2: Request single-use token" : "Step 2 of 2: Enter token & new password"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowForgot(false);
                  setResetStep(1);
                  setForgotError(null);
                  setForgotSuccess(null);
                  setDevTokenHint(null);
                }}
                className="rounded-lg p-1 text-muted hover:bg-surface-alt hover:text-ink transition-colors"
              >
                ✕
              </button>
            </div>

            {forgotError && <Alert tone="danger">{forgotError}</Alert>}
            {forgotSuccess && <Alert tone="success">{forgotSuccess}</Alert>}

            {devTokenHint && resetStep === 2 && (
              <div className="rounded-lg bg-amber-50 border border-amber-200 p-2.5 text-xs text-amber-800">
                <span className="font-semibold">Development mode token:</span>{" "}
                <code className="bg-amber-100 px-1.5 py-0.5 rounded font-mono text-amber-900 break-all">{devTokenHint}</code>
              </div>
            )}

            {resetStep === 1 ? (
              <form className="space-y-3.5" onSubmit={onRequestTokenSubmit}>
                <Field label={t("authIdentifierLabel")} htmlFor="reset_id">
                  <input
                    id="reset_id"
                    className="input"
                    required
                    value={resetIdentifier}
                    onChange={(e) => setResetIdentifier(e.target.value)}
                    placeholder={t("authIdentifierPlaceholder")}
                  />
                </Field>

                <div className="flex justify-between items-center text-xs">
                  <button
                    type="button"
                    onClick={() => setResetStep(2)}
                    className="text-primary hover:underline font-medium"
                  >
                    Already have a reset code?
                  </button>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button type="submit" pending={forgotPending} className="flex-1">
                    Send Reset Code
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setShowForgot(false);
                      setResetStep(1);
                    }}
                  >
                    {t("cancel")}
                  </Button>
                </div>
              </form>
            ) : (
              <form className="space-y-3.5" onSubmit={onResetTokenSubmit}>
                <Field label="Reset Token" htmlFor="reset_token">
                  <input
                    id="reset_token"
                    className="input font-mono text-sm"
                    required
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                    placeholder="Enter 16-character reset token"
                  />
                </Field>

                <Field label={t("resetNewPasswordLabel")} htmlFor="new_password">
                  <input
                    id="new_password"
                    type="password"
                    className="input"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder={t("signupPasswordHint")}
                  />
                </Field>

                <Field label={t("resetConfirmPasswordLabel")} htmlFor="confirm_new_password">
                  <input
                    id="confirm_new_password"
                    type="password"
                    className="input"
                    required
                    value={confirmResetPassword}
                    onChange={(e) => setConfirmResetPassword(e.target.value)}
                  />
                </Field>

                <div className="flex justify-between items-center text-xs">
                  <button
                    type="button"
                    onClick={() => setResetStep(1)}
                    className="text-primary hover:underline font-medium"
                  >
                    ← Back to request code
                  </button>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button type="submit" pending={forgotPending} className="flex-1">
                    {t("resetSubmitBtn")}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setShowForgot(false);
                      setResetStep(1);
                    }}
                  >
                    {t("cancel")}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
