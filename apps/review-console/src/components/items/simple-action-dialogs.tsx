"use client";

import { useState, type ReactElement, type ReactNode } from "react";
import { toast } from "sonner";
import type { ReviewItemDetail } from "@tecnoandes/api-client";
import { ApiError } from "@tecnoandes/api-client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAuth } from "@/lib/auth-context";

async function submit(
  api: ReturnType<typeof useAuth>["api"],
  itemId: number,
  body: Parameters<ReturnType<typeof useAuth>["api"]["postReviewAction"]>[1],
  onDone: () => void,
) {
  try {
    await api.postReviewAction(itemId, body);
    onDone();
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "No se pudo aplicar la acción");
  }
}

/** Aprobar / Descartar: sin datos extra, solo confirman. */
export function InstantActionButton({
  item,
  actionType,
  label,
  variant,
  actor,
  onApplied,
}: {
  item: ReviewItemDetail;
  actionType: "approve" | "discard";
  label: string;
  variant: "default" | "outline" | "destructive";
  actor: string;
  onApplied: () => void;
}) {
  const { api } = useAuth();
  const [busy, setBusy] = useState(false);

  return (
    <Button
      variant={variant}
      disabled={busy}
      data-shortcut={actionType}
      onClick={async () => {
        setBusy(true);
        await submit(api, item.id, { action_type: actionType, actor }, onApplied);
        setBusy(false);
      }}
    >
      {label}
    </Button>
  );
}

function ActionDialog({
  trigger,
  title,
  children,
  onSubmit,
  submitLabel,
  submitDisabled,
}: {
  trigger: ReactElement;
  title: string;
  children: ReactNode;
  onSubmit: () => Promise<void>;
  submitLabel: string;
  submitDisabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={trigger} />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">{children}</div>
        <DialogFooter>
          <Button
            disabled={submitDisabled || busy}
            onClick={async () => {
              setBusy(true);
              await onSubmit();
              setBusy(false);
              setOpen(false);
            }}
          >
            {busy ? "Guardando..." : submitLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function CorrectDialog({
  item,
  actor,
  onApplied,
}: {
  item: ReviewItemDetail;
  actor: string;
  onApplied: () => void;
}) {
  const { api } = useAuth();
  const [correctedAnswer, setCorrectedAnswer] = useState(item.answer);
  const [note, setNote] = useState("");

  return (
    <ActionDialog
      trigger={<Button variant="outline">Corregir</Button>}
      title="Corregir la respuesta"
      submitLabel="Guardar corrección"
      submitDisabled={!correctedAnswer.trim()}
      onSubmit={() =>
        submit(
          api,
          item.id,
          { action_type: "correct", actor, corrected_answer: correctedAnswer, note: note || null },
          onApplied,
        )
      }
    >
      <div className="space-y-1.5">
        <Label>Respuesta corregida</Label>
        <Textarea
          rows={4}
          value={correctedAnswer}
          onChange={(e) => setCorrectedAnswer(e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Nota (opcional)</Label>
        <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
    </ActionDialog>
  );
}

export function EscalateDialog({
  item,
  actor,
  onApplied,
}: {
  item: ReviewItemDetail;
  actor: string;
  onApplied: () => void;
}) {
  const { api } = useAuth();
  const [note, setNote] = useState("");

  return (
    <ActionDialog
      trigger={
        <Button variant="outline" data-shortcut="escalate">
          Escalar (E)
        </Button>
      }
      title="Escalar a un asesor"
      submitLabel="Escalar"
      submitDisabled={!note.trim()}
      onSubmit={() =>
        submit(api, item.id, { action_type: "escalate", actor, note }, onApplied)
      }
    >
      <div className="space-y-1.5">
        <Label>Nota (requerida)</Label>
        <Textarea
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="¿Por qué se escala este caso?"
        />
      </div>
    </ActionDialog>
  );
}

export function CorrectAndCreateDocumentDialog({
  item,
  actor,
  onApplied,
}: {
  item: ReviewItemDetail;
  actor: string;
  onApplied: () => void;
}) {
  const { api } = useAuth();
  const [correctedAnswer, setCorrectedAnswer] = useState(item.answer);
  const [note, setNote] = useState("");
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("faq");
  const [content, setContent] = useState(`## ${item.question}\n\n`);

  const valid = slug.trim() && title.trim() && category.trim() && content.trim() && correctedAnswer.trim();

  return (
    <ActionDialog
      trigger={<Button variant="outline">Corregir + crear documento</Button>}
      title="Crear un documento nuevo para esta brecha"
      submitLabel="Crear documento y corregir"
      submitDisabled={!valid}
      onSubmit={() =>
        submit(
          api,
          item.id,
          {
            action_type: "correct_and_create_document",
            actor,
            corrected_answer: correctedAnswer,
            note: note || null,
            new_document: { slug, title, category, content },
          },
          onApplied,
        )
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>Slug</Label>
          <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="productos-x" />
        </div>
        <div className="space-y-1.5">
          <Label>Categoría</Label>
          <Input value={category} onChange={(e) => setCategory(e.target.value)} />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label>Título</Label>
        <Input value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label>Contenido (Markdown)</Label>
        <Textarea rows={6} value={content} onChange={(e) => setContent(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label>Respuesta corregida para este caso</Label>
        <Textarea
          rows={3}
          value={correctedAnswer}
          onChange={(e) => setCorrectedAnswer(e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Nota (opcional)</Label>
        <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
    </ActionDialog>
  );
}
