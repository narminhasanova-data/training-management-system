import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, session } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => session.get()?.user ?? null);

  useEffect(() => {
    const signedOut = () => setUser(null);
    window.addEventListener("tms:signed-out", signedOut);
    if (session.get()) api("auth/me/").then(setUser).catch(() => {});
    return () => window.removeEventListener("tms:signed-out", signedOut);
  }, []);

  const signIn = useCallback(async (username, password) => {
    const data = await api("auth/login/", { method: "POST", body: { username, password } });
    session.set(data);
    setUser(data.user);
  }, []);

  const signOut = useCallback(async () => {
    await api("auth/logout/", { method: "POST" }).catch(() => {});
    session.set(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, signIn, signOut }), [user, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
