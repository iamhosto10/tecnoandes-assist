"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, type createApiClient } from "@tecnoandes/api-client";
import { useAuth } from "./auth-context";

type ApiClient = ReturnType<typeof createApiClient>;

// Patrón compartido de fetch para las páginas de la consola: pide algo
// con el cliente autenticado, y si el token resultó inválido (401) cierra
// la sesión en vez de mostrar un error genérico.
export function useApiResource<T>(
  fetcher: (api: ApiClient) => Promise<T>,
  deps: unknown[],
) {
  const { api, logout } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher(api)
      .then((result) => setData(result))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) {
          logout();
          return;
        }
        setError(err instanceof Error ? err.message : "Error desconocido");
      })
      .finally(() => setLoading(false));
    // `deps` es un array dinámico a propósito: este hook es genérico y cada
    // página le pasa sus propias dependencias. El linter no puede verificar
    // estáticamente un array que no es literal, pero el patrón es correcto.
    // eslint-disable-next-line react-hooks/use-memo, react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}
