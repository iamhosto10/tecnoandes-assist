"use client";

import { useState } from "react";
import { toast } from "sonner";
import { ApiError, type RetestResponse } from "@tecnoandes/api-client";
import { Button } from "@/components/ui/button";
import { DecisionBadge } from "@/components/shared/badges";
import { useAuth } from "@/lib/auth-context";

function Snapshot({ label, snapshot }: { label: string; snapshot: RetestResponse["before"] }) {
  return (
    <div className="space-y-1.5 rounded-md border p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <DecisionBadge decision={snapshot.decision} />
      </div>
      <p className="text-sm">{snapshot.answer}</p>
      <p className="text-xs text-muted-foreground">
        Confianza: <span className="font-mono">{snapshot.confidence_score.toFixed(1)}</span> ·
        Soporte: <span className="font-mono">{snapshot.support ?? "—"}</span>
      </p>
    </div>
  );
}

export function RetestPanel({ itemId }: { itemId: number }) {
  const { api } = useAuth();
  const [result, setResult] = useState<RetestResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleRetest() {
    setLoading(true);
    try {
      const response = await api.retestReviewItem(itemId);
      setResult(response);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "No se pudo re-probar el caso");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Re-probar
        </h2>
        <Button size="sm" variant="outline" onClick={handleRetest} disabled={loading}>
          {loading ? "Probando..." : "Re-probar con la base actual"}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Vuelve a correr la pregunta contra la base de conocimiento actual, sin crear un caso
        nuevo — útil después de editar un documento para confirmar que la respuesta mejoró.
      </p>
      {result && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Snapshot label="Antes" snapshot={result.before} />
          <Snapshot label="Después" snapshot={result.after} />
        </div>
      )}
    </div>
  );
}
