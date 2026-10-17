import { HOME_BY_ROLE, useAuth } from "../../auth/AuthContext";
import { TextLink } from "../../components/ui";

function StatusPage({ code, title, message }: { code: string; title: string; message: string }) {
  const { user } = useAuth();
  return (
    <div className="grid min-h-screen place-items-center px-6">
      <div className="max-w-md">
        <p className="text-sm font-semibold text-muted">{code}</p>
        <h1 className="mt-1 text-2xl font-bold">{title}</h1>
        <p className="mt-2 text-muted">{message}</p>
        <p className="mt-6"><TextLink to={user ? HOME_BY_ROLE[user.role] : "/login"}>{user ? "Go to your dashboard" : "Sign in"}</TextLink></p>
      </div>
    </div>
  );
}

export const UnauthorizedPage = () => (
  <StatusPage code="403" title="You don’t have access to this page"
    message="Your role can’t open this area. If you need it for your work, ask the operations team to review your account." />
);

export const NotFoundPage = () => (
  <StatusPage code="404" title="Page not found" message="The address may be mistyped, or the page has moved." />
);
