import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { auth as authApi } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => authApi.getStoredUser());
  const [checking, setChecking] = useState(true);

  // On mount, verify the stored token is still valid against the backend
  // rather than trusting localStorage blindly.
  useEffect(() => {
    const token = authApi.getToken();
    if (!token) {
      setChecking(false);
      return;
    }
    authApi
      .me()
      .then((freshUser) => {
        setUser(freshUser);
        authApi.saveSession(token, freshUser);
      })
      .catch(() => {
        authApi.clearSession();
        setUser(null);
      })
      .finally(() => setChecking(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const { token, user: u } = await authApi.login(email, password);
    authApi.saveSession(token, u);
    setUser(u);
    return u;
  }, []);

  const register = useCallback(async (name, email, password) => {
    const { token, user: u } = await authApi.register(name, email, password);
    authApi.saveSession(token, u);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(() => {
    authApi.clearSession();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, checking, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
