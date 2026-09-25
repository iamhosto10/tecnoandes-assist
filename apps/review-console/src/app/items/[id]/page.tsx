"use client";

import { useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfidencePanel } from "@/components/shared/confidence-panel";
import { StatusBadge, DecisionBadge, ReasonBadge } from "@/components/shared/badges";
import { ActionPanel } from "@/components/items/action-panel";
import { RetestPanel } from "@/components/items/retest-panel";
import { useApiResource } from "@/lib/use-api-resource";
import { useKeyboardShortcuts } from "@/lib/use-keyboard-shortcuts";

export default function ItemDetailPage() {
  const params = useParams<{ id: string }>();
  const itemId = Number(params.id);
  const router = useRouter();

  const {
    data: item,
    loading,
    reload,
  } = useApiResource((api) => api.getReviewItem(itemId), [itemId]);

  // Lista liviana de pendientes para saber "siguiente/anterior" con J/K,
  // sin importar desde qué filtro se abrió este caso.
  const { data: siblings } = useApiResource(
    (api) => api.getReviewItems({ status: "pending", limit: 100 }),
    [],
  );

  const { prevId, nextId } = useMemo(() => {
    if (!siblings) return { prevId: null as number | null, nextId: null as number | null };
    const ids = siblings.items.map((i) => i.id);
    const index = ids.indexOf(itemId);
    return {
      prevId: index > 0 ? ids[index - 1] : null,
      nextId: index >= 0 && index < ids.length - 1 ? ids[index + 1] : null,
    };
  }, [siblings, itemId]);

  useKeyboardShortcuts({
    j: () => nextId && router.push(`/items/${nextId}`),
    k: () => prevId && router.push(`/items/${prevId}`),
    a: () =>
      document.querySelector<HTMLButtonElement>('[data-shortcut="approve"]')?.click(),
    e: () =>
      document.querySelector<HTMLButtonElement>('[data-shortcut="escalate"]')?.click(),
    d: () =>
      document.querySelector<HTMLButtonElement>('[data-shortcut="discard"]')?.click(),
  });

  if (loading || !item) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-6">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[1fr_380px]">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
            ← Cola
          </Button>
          <div className="flex gap-2">
            <StatusBadge status={item.status} />
            <DecisionBadge decision={item.decision} />
            <ReasonBadge reason={item.reason} />
          </div>
        </div>

        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Usa J/K para moverse entre casos pendientes, ? para ver los atajos.</span>
          <span>
            {prevId && "← "}
            {nextId && "→"}
          </span>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Pregunta
          </h2>
          <p className="mt-1">{item.question}</p>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Respuesta que vio el cliente
          </h2>
          <p className="mt-1 whitespace-pre-wrap">{item.answer}</p>
          {item.raw_model_answer && item.raw_model_answer !== item.answer && (
            <>
              <h2 className="mt-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Respuesta cruda del modelo
              </h2>
              <p className="mt-1 whitespace-pre-wrap text-muted-foreground">
                {item.raw_model_answer}
              </p>
            </>
          )}
        </div>

        <ActionPanel
          item={item}
          onActionApplied={() => {
            toast.success("Acción aplicada");
            reload();
          }}
        />

        <RetestPanel itemId={item.id} />

        {item.actions.length > 0 && (
          <div className="rounded-lg border bg-card p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Historial de acciones
            </h2>
            <ul className="mt-2 space-y-2 text-xs">
              {item.actions.map((a) => (
                <li
                  key={a.id}
                  className="border-t border-border/60 pt-2 first:border-t-0 first:pt-0"
                >
                  <span className="font-medium">{a.action_type}</span> — {a.actor}
                  {a.note && <p className="text-muted-foreground">{a.note}</p>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <ConfidencePanel
        confidence={item.confidence}
        sources={item.sources}
        ruleApplied={item.rule_applied}
      />
    </div>
  );
}
