"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { createApiClient } from "@tecnoandes/api-client";

const STORAGE_KEY = "tecnoandes_review_console_token";

// Público a propósito: coincide con el puerto por defecto de docker-compose,
// así no hace falta .env.local para desarrollo local.
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ApiClient = ReturnType<typeof createApiClient>;

interface AuthContextValue {
  token: string | null;
  setToken: (token: string) => void;
  logout: () => void;
  api: ApiClient;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  // Evita un parpadeo mostrando el login antes de terminar de leer
  // localStorage (que solo existe en el cliente).
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    // localStorage no existe durante el render en el servidor — leerlo
    // fuera de un efecto causaría un mismatch de hidratación.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTokenState(window.localStorage.getItem(STORAGE_KEY));
    setHydrated(true);
  }, []);

  function setToken(value: string) {
    window.localStorage.setItem(STORAGE_KEY, value);
    setTokenState(value);
  }

  function logout() {
    window.localStorage.removeItem(STORAGE_KEY);
    setTokenState(null);
  }

  const api = createApiClient({ baseUrl: API_BASE_URL, reviewToken: token ?? undefined });

  if (!hydrated) return null;

  return (
    <AuthContext.Provider value={{ token, setToken, logout, api }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
