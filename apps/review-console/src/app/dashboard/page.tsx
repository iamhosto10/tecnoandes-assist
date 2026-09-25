"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DecisionBadge } from "@/components/shared/badges";
import { useApiResource } from "@/lib/use-api-resource";
import type { Decision } from "@tecnoandes/api-client";

const DECISIONS: Decision[] = ["direct", "warn", "review", "escalate"];

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: summary, loading: loadingSummary } = useApiResource(
    (api) => api.getDashboardSummary(),
    [],
  );
  const { data: runsData, loading: loadingRuns } = useApiResource(
    (api) => api.getEvaluationRuns(),
    [],
  );

  const maxDecisionCount = summary
    ? Math.max(1, ...DECISIONS.map((d) => summary.decision_counts[d] ?? 0))
    : 1;

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Un vistazo a la operación: cuántas preguntas se respondieron, cómo se enrutaron, y
          cómo le fue al pipeline en la última corrida de <code>make eval</code>.
        </p>
      </div>

      {loadingSummary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {summary && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Preguntas totales" value={String(summary.total_queries)} />
            <Stat label="Casos pendientes" value={String(summary.pending_review_count)} />
            <Stat label="Documentos activos" value={String(summary.document_count)} />
            <Stat
              label="Confianza promedio"
              value={
                summary.avg_confidence_score !== null
                  ? summary.avg_confidence_score.toFixed(1)
                  : "—"
              }
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Distribución de decisiones</CardTitle>
              <CardDescription>
                Cómo enrutó el sistema las {summary.total_queries} preguntas que ha recibido.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {DECISIONS.map((decision) => {
                const count = summary.decision_counts[decision] ?? 0;
                const pct = (count / maxDecisionCount) * 100;
                return (
                  <div key={decision} className="flex items-center gap-3">
                    <div className="w-24 shrink-0">
                      <DecisionBadge decision={decision} />
                    </div>
                    <div className="h-5 flex-1 overflow-hidden rounded bg-muted">
                      <div
                        className="h-full rounded bg-primary/70"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-10 shrink-0 text-right font-mono text-sm">{count}</span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 gap-3">
            <Stat
              label="Latencia promedio"
              value={
                summary.avg_latency_ms !== null
                  ? `${Math.round(summary.avg_latency_ms)} ms`
                  : "—"
              }
            />
            <Stat label="Costo total (LLM)" value={`$${summary.total_cost_usd.toFixed(4)}`} />
          </div>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Corridas de evaluación</CardTitle>
          <CardDescription>
            Historial de <code>make eval</code> — recall@k, precisión de enrutamiento y veredicto
            del juez sobre eval/seed.jsonl.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingRuns && <Skeleton className="h-24 w-full" />}
          {!loadingRuns && runsData?.runs.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Todavía no se ha corrido <code>make eval</code>.
            </p>
          )}
          {runsData && runsData.runs.length > 0 && (
            <div className="divide-y">
              {runsData.runs.map((run) => (
                <div key={run.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                  <span className="text-muted-foreground">
                    #{run.id} · {new Date(run.created_at).toLocaleString("es-CO")}
                  </span>
                  <div className="flex flex-wrap gap-3 font-mono text-xs">
                    <span>casos: {String(run.metrics.total_cases ?? "—")}</span>
                    <span>
                      enrutamiento:{" "}
                      {run.metrics.routing_accuracy != null
                        ? `${Math.round(Number(run.metrics.routing_accuracy) * 100)}%`
                        : "—"}
                    </span>
                    <span>
                      recall@k:{" "}
                      {run.metrics.mean_recall_at_k != null
                        ? Number(run.metrics.mean_recall_at_k).toFixed(2)
                        : "—"}
                    </span>
                    <span>
                      juez:{" "}
                      {run.metrics.judge_correct_rate != null
                        ? `${Math.round(Number(run.metrics.judge_correct_rate) * 100)}%`
                        : "—"}
                    </span>
                    <span>costo: ${Number(run.metrics.total_cost_usd ?? 0).toFixed(4)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
