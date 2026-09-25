"use client";

import { useState, type FormEvent } from "react";
import { ApiError, createApiClient } from "@tecnoandes/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth, API_BASE_URL } from "@/lib/auth-context";

export function LoginForm() {
  const { setToken } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;

    setChecking(true);
    setError(null);
    // Valida el token de una vez, en vez de guardarlo a ciegas y que el
    // usuario descubra que estaba mal en la primera pantalla que visite.
    const client = createApiClient({ baseUrl: API_BASE_URL, reviewToken: trimmed });
    try {
      await client.getReviewItems({ limit: 1 });
      setToken(trimmed);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Token inválido.");
      } else {
        setError(`No se pudo conectar con el backend en ${API_BASE_URL}.`);
      }
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="flex h-dvh items-center justify-center bg-muted/30 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Consola de revisión</CardTitle>
          <CardDescription>TecnoAndes Assist</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="token">Token de acceso</Label>
              <Input
                id="token"
                type="password"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                autoFocus
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={checking || !value.trim()}>
              {checking ? "Verificando..." : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
