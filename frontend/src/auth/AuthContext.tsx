import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { tokenStore } from "../api/client";
import { authApi } from "../api/endpoints";
import type { Role, SignupInput, User } from "../api/types";

interface AuthState {
  user: User | null;
  ready: boolean;
  login: (identifier: string, password: string) => Promise<User>;
  signup: (input: SignupInput) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export const HOME_BY_ROLE: Record<Role, string> = { LEARNER: "/learner", SECURITY: "/security", ADMIN: "/ops" };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  // Restore the session after a page refresh by asking the server who we are.
  useEffect(() => {
    if (!tokenStore.get()) {
      setReady(true);
      return;
    }
    authApi.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setReady(true));
  }, []);

  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener("cdms:unauthorized", onUnauthorized);
    return () => window.removeEventListener("cdms:unauthorized", onUnauthorized);
  }, []);

  const login = useCallback(async (identifier: string, password: string) => {
    const result = await authApi.login(identifier, password);
    tokenStore.set(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  const signup = useCallback(async (input: SignupInput) => {
    const result = await authApi.signup(input);
    tokenStore.set(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, ready, login, signup, logout }), [user, ready, login, signup, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** Signed-in user; only call inside a route guarded by RequireRole. */
export function useUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error("No signed-in user");
  return user;
}
