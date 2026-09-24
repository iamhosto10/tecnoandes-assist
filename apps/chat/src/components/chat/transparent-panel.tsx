import type { AskResponse, ScoreComponent } from "@tecnoandes/api-client";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// Mapeo puramente descriptivo (no duplica los umbrales numéricos reales,
// que viven en app/core/config.py del backend) — solo le pone palabras a
// qué regla de app/confidence/rules.py disparó la decisión.
const RULE_LABELS: Record<string, string> = {
  needs_human: "El modelo marcó needs_human=true → se escala.",
  generation_error: "Falló la generación (API, salida inválida) → a revisión.",
  invalid_citation: "El modelo citó un chunk fuera del contexto → a revisión.",
  no_support: "support=none: el contexto no respalda la respuesta → a revisión.",
  partial_support: "support=partial: falta un dato → responde con advertencia.",
  low_score: "El puntaje quedó por debajo del umbral bajo → a revisión.",
  mid_score: "El puntaje quedó entre el umbral bajo y el alto → advertencia.",
  high_score: "El puntaje superó el umbral alto → respuesta directa.",
};

function ScoreRow({
  label,
  component,
}: {
  label: string;
  component: ScoreComponent;
}) {
  return (
    <div className="flex items-center justify-between gap-2 text-xs">
      <span className="text-muted-foreground">
        {label}{" "}
        <span className="text-muted-foreground/70">
          (peso {Math.round(component.weight * 100)}%, normalizado{" "}
          {component.normalized_value.toFixed(2)})
        </span>
      </span>
      <span className="font-mono font-medium">
        {component.points.toFixed(1)} pts
      </span>
    </div>
  );
}

export function TransparentPanel({ response }: { response: AskResponse }) {
  const { confidence, sources, rule_applied, latency_ms, cost_usd } = response;
  const { score_breakdown } = confidence;

  return (
    <div className="mt-3 space-y-4 rounded-lg border bg-card p-4 text-card-foreground">
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Señales
        </h4>
        <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-3">
          <div>
            <span className="text-muted-foreground">retrieval_score: </span>
            <span className="font-mono">{confidence.retrieval_score.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">retrieval_margin: </span>
            <span className="font-mono">{confidence.retrieval_margin.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">support: </span>
            <span className="font-mono">{confidence.support ?? "—"}</span>
          </div>
          <div>
            <span className="text-muted-foreground">needs_human: </span>
            <span className="font-mono">{String(confidence.needs_human)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">citation_valid: </span>
            <span className="font-mono">{String(confidence.citation_valid)}</span>
          </div>
        </div>
      </div>

      <Separator />

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Cálculo del puntaje
        </h4>
        <div className="mt-2 space-y-1.5">
          <ScoreRow label="Similitud de búsqueda" component={score_breakdown.retrieval_score} />
          <ScoreRow label="Margen 1ro vs. 2do" component={score_breakdown.retrieval_margin} />
          <ScoreRow label="Soporte del modelo" component={score_breakdown.support} />
          <Separator className="my-1.5" />
          <div className="flex items-center justify-between text-sm font-semibold">
            <span>Puntaje final</span>
            <span className="font-mono">{confidence.confidence_score.toFixed(1)} / 100</span>
          </div>
        </div>
      </div>

      <Separator />

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Regla aplicada
        </h4>
        <p className="mt-1 text-xs">
          <Badge variant="outline" className="mr-1.5 font-mono text-[10px]">
            {rule_applied}
          </Badge>
          {RULE_LABELS[rule_applied] ?? "Sin descripción para esta regla."}
        </p>
      </div>

      <Separator />

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Chunks recuperados
        </h4>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[420px] text-left text-xs">
            <thead>
              <tr className="text-muted-foreground">
                <th className="pb-1 pr-2 font-normal">Documento</th>
                <th className="pb-1 pr-2 font-normal">Vector</th>
                <th className="pb-1 pr-2 font-normal">Texto</th>
                <th className="pb-1 font-normal">RRF</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.chunk_id} className="border-t border-border/60">
                  <td className="py-1 pr-2">
                    {s.document_title}
                    {s.cited && (
                      <Badge variant="secondary" className="ml-1.5 text-[9px]">
                        citado
                      </Badge>
                    )}
                  </td>
                  <td className="py-1 pr-2 font-mono">{s.vector_score.toFixed(3)}</td>
                  <td className="py-1 pr-2 font-mono">{s.fulltext_score.toFixed(3)}</td>
                  <td className="py-1 font-mono">{s.rrf_score.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Separator />

      <div className="flex gap-4 text-xs text-muted-foreground">
        <span>Latencia: {latency_ms} ms</span>
        <span>Costo: ${cost_usd.toFixed(6)} USD</span>
      </div>
    </div>
  );
}
