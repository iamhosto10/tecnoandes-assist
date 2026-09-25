"use client";

import { useState } from "react";
import type { ReviewItemDetail } from "@tecnoandes/api-client";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  CorrectAndCreateDocumentDialog,
  CorrectDialog,
  EscalateDialog,
  InstantActionButton,
} from "./simple-action-dialogs";
import { EditDocumentActionDialog } from "./edit-document-action-dialog";

export function ActionPanel({
  item,
  onActionApplied,
}: {
  item: ReviewItemDetail;
  onActionApplied: () => void;
}) {
  const [actor, setActor] = useState("reviewer");

  const resolved = item.status !== "pending";

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-3 flex items-end justify-between gap-3">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Acciones
        </h2>
        <div className="flex items-center gap-2">
          <Label htmlFor="actor" className="text-xs text-muted-foreground">
            Revisor
          </Label>
          <Input
            id="actor"
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            className="h-7 w-32 text-xs"
          />
        </div>
      </div>

      {resolved ? (
        <p className="text-sm text-muted-foreground">
          Este caso ya se resolvió ({item.status}) — usa &quot;Re-probar&quot; abajo si acabas de
          editar la base de conocimiento y quieres confirmar que mejoró.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          <InstantActionButton
            item={item}
            actionType="approve"
            label="Aprobar (A)"
            variant="default"
            actor={actor}
            onApplied={onActionApplied}
          />
          <CorrectDialog item={item} actor={actor} onApplied={onActionApplied} />
          <CorrectAndCreateDocumentDialog item={item} actor={actor} onApplied={onActionApplied} />
          <EditDocumentActionDialog item={item} actor={actor} onApplied={onActionApplied} />
          <EscalateDialog item={item} actor={actor} onApplied={onActionApplied} />
          <InstantActionButton
            item={item}
            actionType="discard"
            label="Descartar (D)"
            variant="destructive"
            actor={actor}
            onApplied={onActionApplied}
          />
        </div>
      )}
    </div>
  );
}
