import { HOME_BY_ROLE, useAuth } from "../../auth/AuthContext";
import { TextLink } from "../../components/ui";
import { useLanguage } from "../../i18n/LanguageContext";

function StatusPage({ code, title, message }: { code: string; title: string; message: string }) {
  const { user } = useAuth();
  const { t } = useLanguage();
  return (
    <div className="grid min-h-screen place-items-center px-6">
      <div className="max-w-md text-center">
        <p className="text-sm font-semibold text-primary-700 font-mono">{code}</p>
        <h1 className="mt-1 text-2xl font-bold font-serif text-ink">{title}</h1>
        <p className="mt-2 text-muted">{message}</p>
        <p className="mt-6">
          <TextLink to={user ? HOME_BY_ROLE[user.role] : "/login"}>
            {user ? t("goToDashboard") : t("authSignInBtn")}
          </TextLink>
        </p>
      </div>
    </div>
  );
}

export function UnauthorizedPage() {
  const { t } = useLanguage();
  return <StatusPage code="403" title={t("err403Title")} message={t("err403Msg")} />;
}

export function NotFoundPage() {
  const { t } = useLanguage();
  return <StatusPage code="404" title={t("err404Title")} message={t("err404Msg")} />;
}
