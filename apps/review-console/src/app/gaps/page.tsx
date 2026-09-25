"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useApiResource } from "@/lib/use-api-resource";

export default function GapsPage() {
  const router = useRouter();
  const { data: groups, loading } = useApiResource((api) => api.getKnowledgeGaps(2), []);

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-lg font-semibold">Brechas de conocimiento</h1>
        <p className="text-sm text-muted-foreground">
          Preguntas que la base de conocimiento no pudo responder (support=none), agrupadas por
          similitud — patrones que valen un documento nuevo, no casos aislados.
        </p>
      </div>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      )}

      {!loading && groups?.length === 0 && (
        <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          Todavía no hay grupos de 2 o más preguntas sin soporte. Los casos individuales igual
          aparecen en la cola con motivo &quot;Sin soporte&quot;.
        </p>
      )}

      <div className="space-y-3">
        {groups?.map((group, index) => (
          <div key={index} className="rounded-lg border bg-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">
                  {group.count} {group.count === 1 ? "persona preguntó" : "personas preguntaron"}{" "}
                  algo como:
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  &quot;{group.representative_question}&quot;
                </p>
              </div>
              <Button
                size="sm"
                onClick={() =>
                  router.push(
                    `/documents/new?hint=${encodeURIComponent(group.representative_question)}`,
                  )
                }
              >
                Crear documento
              </Button>
            </div>
            {group.example_questions.length > 1 && (
              <details className="mt-2 text-xs text-muted-foreground">
                <summary className="cursor-pointer">
                  Ver las {group.example_questions.length} preguntas del grupo
                </summary>
                <ul className="mt-1 list-inside list-disc space-y-0.5">
                  {group.example_questions.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ul>
              </details>
            )}
            <Link
              href={`/?status=all`}
              className="mt-2 inline-block text-xs text-primary hover:underline"
            >
              Ver los {group.query_ids.length} casos individuales en la cola
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
