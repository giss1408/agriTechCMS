import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ReactNode, createContext, useContext, useEffect, useSyncExternalStore } from "react";
import { api, isLoggedIn, onAuthChange, setTokens } from "./api";
import type { Me } from "./types";

type AuthState = { me: Me | null; loading: boolean; logout: () => void };
const AuthCtx = createContext<AuthState>({ me: null, loading: true, logout: () => {} });
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const loggedIn = useSyncExternalStore(onAuthChange, isLoggedIn);
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.get<Me>("/users/me"), enabled: loggedIn, retry: false });

  useEffect(() => {
    if (!loggedIn) qc.clear();
  }, [loggedIn, qc]);

  const value: AuthState = {
    me: loggedIn ? me.data ?? null : null,
    loading: loggedIn && me.isLoading,
    logout: () => setTokens(null),
  };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
