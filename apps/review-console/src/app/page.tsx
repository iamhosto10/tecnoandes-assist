"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { ReviewStatus } from "@tecnoandes/api-client";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge, DecisionBadge, ReasonBadge, REASON_LABELS } from "@/components/shared/badges";
import { useAuth } from "@/lib/auth-context";
import { useApiResource } from "@/lib/use-api-resource";
import { cn } from "@/lib/utils";

const STATUSES: ReviewStatus[] = ["pending", "approved", "corrected", "escalated", "discarded"];
const PAGE_SIZE = 20;

function useStatusCounts() {
  const { api } = useAuth();
  const [counts, setCounts] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    Promise.all(
      STATUSES.map((status) =>
        api.getReviewItems({ status, limit: 1 }).then((r) => [status, r.total] as const),
      ),
    ).then((entries) => setCounts(Object.fromEntries(entries)));
  }, [api]);

  return counts;
}

export default function QueuePage() {
  const router = useRouter();
  const [status, setStatus] = useState<string>("pending");
  const [reason, setReason] = useState<string>("all");
  const [confidenceMin, setConfidenceMin] = useState("");
  const [confidenceMax, setConfidenceMax] = useState("");
  const [offset, setOffset] = useState(0);

  const counts = useStatusCounts();

  const { data, loading } = useApiResource(
    (api) =>
      api.getReviewItems({
        status: status === "all" ? undefined : status,
        reason: reason === "all" ? undefined : reason,
        confidence_min: confidenceMin ? Number(confidenceMin) : undefined,
        confidence_max: confidenceMax ? Number(confidenceMax) : undefined,
        limit: PAGE_SIZE,
        offset,
      }),
    [status, reason, confidenceMin, confidenceMax, offset],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-4 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap gap-2">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => {
              setStatus(s);
              setOffset(0);
            }}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              status === s ? "border-primary bg-accent" : "border-border hover:bg-muted",
            )}
          >
            <StatusBadge status={s} /> <span className="ml-1 font-mono">{counts?.[s] ?? "…"}</span>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-card p-3">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Motivo</label>
          <Select
            value={reason}
            onValueChange={(v) => {
              setReason(v ?? "all");
              setOffset(0);
            }}
          >
            <SelectTrigger className="w-44">
              {/* Select.Value renderiza el `value` crudo por defecto en Base
                  UI (a diferencia de Radix) — hay que mapearlo a mano. */}
              <SelectValue>
                {(value: string) => (value === "all" ? "Todos" : REASON_LABELS[value as keyof typeof REASON_LABELS])}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="needs_human">Necesita humano</SelectItem>
              <SelectItem value="generation_error">Error de generación</SelectItem>
              <SelectItem value="invalid_citation">Cita inválida</SelectItem>
              <SelectItem value="no_support">Sin soporte</SelectItem>
              <SelectItem value="partial_support">Soporte parcial</SelectItem>
              <SelectItem value="low_score">Puntaje bajo</SelectItem>
              <SelectItem value="mid_score">Puntaje medio</SelectItem>
              <SelectItem value="high_score">Puntaje alto</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Confianza mín.</label>
          <Input
            type="number"
            className="w-24"
            value={confidenceMin}
            onChange={(e) => {
              setConfidenceMin(e.target.value);
              setOffset(0);
            }}
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Confianza máx.</label>
          <Input
            type="number"
            className="w-24"
            value={confidenceMax}
            onChange={(e) => {
              setConfidenceMax(e.target.value);
              setOffset(0);
            }}
          />
        </div>
      </div>

      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Pregunta</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Motivo</TableHead>
              <TableHead>Decisión</TableHead>
              <TableHead className="text-right">Confianza</TableHead>
              <TableHead className="text-right">Fecha</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading &&
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))}
            {!loading && data?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  No hay casos con estos filtros.
                </TableCell>
              </TableRow>
            )}
            {data?.items.map((item) => (
              <TableRow
                key={item.id}
                className="cursor-pointer"
                onClick={() => router.push(`/items/${item.id}`)}
              >
                <TableCell className="max-w-xs truncate">{item.question}</TableCell>
                <TableCell>
                  <StatusBadge status={item.status} />
                </TableCell>
                <TableCell>
                  <ReasonBadge reason={item.reason} />
                </TableCell>
                <TableCell>
                  <DecisionBadge decision={item.decision} />
                </TableCell>
                <TableCell className="text-right font-mono">
                  {item.confidence_score.toFixed(1)}
                </TableCell>
                <TableCell className="text-right text-xs text-muted-foreground">
                  {new Date(item.created_at).toLocaleString("es-CO")}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {data && data.total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {offset + 1}-{Math.min(offset + PAGE_SIZE, data.total)} de {data.total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= data.total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
