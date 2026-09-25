import type { Decision, ReviewStatus, RuleApplied } from "@tecnoandes/api-client";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<ReviewStatus, string> = {
  pending: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300",
  approved: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-300",
  corrected: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-300",
  escalated: "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-300",
  discarded: "bg-muted text-muted-foreground",
};

const STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: "Pendiente",
  approved: "Aprobado",
  corrected: "Corregido",
  escalated: "Escalado",
  discarded: "Descartado",
};

export function StatusBadge({ status }: { status: ReviewStatus }) {
  return (
    <Badge variant="outline" className={cn("border-transparent", STATUS_STYLES[status])}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}

const DECISION_STYLES: Record<Decision, string> = {
  direct: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-300",
  warn: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300",
  review: "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-300",
  escalate: "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-300",
};

export function DecisionBadge({ decision }: { decision: Decision }) {
  return (
    <Badge variant="outline" className={cn("border-transparent", DECISION_STYLES[decision])}>
      {decision}
    </Badge>
  );
}

// Puramente descriptivo — no duplica los umbrales numéricos reales
// (viven en app/core/config.py del backend), solo le pone una etiqueta
// corta en español a cada motivo. Exportado para reusarlo en el filtro
// de la cola (app/page.tsx), donde Select.Value también lo necesita.
export const REASON_LABELS: Record<RuleApplied, string> = {
  needs_human: "Necesita humano",
  generation_error: "Error de generación",
  invalid_citation: "Cita inválida",
  no_support: "Sin soporte",
  partial_support: "Soporte parcial",
  low_score: "Puntaje bajo",
  mid_score: "Puntaje medio",
  high_score: "Puntaje alto",
};

export function ReasonBadge({ reason }: { reason: RuleApplied }) {
  return <Badge variant="secondary">{REASON_LABELS[reason] ?? reason}</Badge>;
}
