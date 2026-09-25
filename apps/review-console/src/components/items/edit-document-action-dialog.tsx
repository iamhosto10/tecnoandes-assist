"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiError, type ReviewItemDetail } from "@tecnoandes/api-client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { DiffView } from "@/components/shared/diff-view";
import { useAuth } from "@/lib/auth-context";

export function EditDocumentActionDialog({
  item,
  actor,
  onApplied,
}: {
  item: ReviewItemDetail;
  actor: string;
  onApplied: () => void;
}) {
  const { api } = useAuth();
  const [open, setOpen] = useState(false);
  const [documentId, setDocumentId] = useState<number | null>(null);
  const [originalContent, setOriginalContent] = useState("");
  const [content, setContent] = useState("");
  const [correctedAnswer, setCorrectedAnswer] = useState(item.answer);
  const [note, setNote] = useState("");
  const [loadingDoc, setLoadingDoc] = useState(false);
  const [busy, setBusy] = useState(false);

  // Documentos únicos entre las fuentes recuperadas del caso — es lo más
  // probable que el revisor quiera editar, sin tener que ir a buscarlo
  // por separado en la base de conocimiento.
  const documentOptions = Array.from(
    new Map(item.sources.map((s) => [s.document_id, s])).values(),
  );

  useEffect(() => {
    if (documentId === null) return;
    // Trae el contenido del documento elegido en el select — un fetch de
    // verdad en respuesta a una selección, no un simple derivar-de-props.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingDoc(true);
    api
      .getDocument(documentId)
      .then((doc) => {
        setOriginalContent(doc.content);
        setContent(doc.content);
      })
      .finally(() => setLoadingDoc(false));
  }, [documentId, api]);

  async function handleSubmit() {
    if (documentId === null) return;
    setBusy(true);
    try {
      await api.postReviewAction(item.id, {
        action_type: "correct_and_edit_document",
        actor,
        corrected_answer: correctedAnswer,
        note: note || null,
        document_id: documentId,
        document_content: content,
      });
      setOpen(false);
      onApplied();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "No se pudo aplicar la acción");
    } finally {
      setBusy(false);
    }
  }

  const valid = documentId !== null && content.trim() && correctedAnswer.trim();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline">Corregir + editar documento</Button>} />
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar un documento existente</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Documento a editar</Label>
            <Select
              value={documentId?.toString() ?? ""}
              onValueChange={(v) => setDocumentId(Number(v))}
            >
              <SelectTrigger>
                {/* Select.Value renderiza el `value` crudo por defecto en Base
                    UI (a diferencia de Radix) — hay que mapearlo a la
                    etiqueta a mano. */}
                <SelectValue placeholder="Elige un documento de las fuentes de este caso">
                  {(value: string) =>
                    documentOptions.find((s) => String(s.document_id) === value)
                      ?.document_title ?? "Elige un documento de las fuentes de este caso"
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {documentOptions.map((s) => (
                  <SelectItem key={s.document_id} value={String(s.document_id)}>
                    {s.document_title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loadingDoc && <p className="text-xs text-muted-foreground">Cargando documento...</p>}

          {documentId !== null && !loadingDoc && (
            <>
              <div className="space-y-1.5">
                <Label>Contenido (Markdown)</Label>
                <Textarea
                  rows={10}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="font-mono text-xs"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Vista de diferencias</Label>
                <DiffView oldText={originalContent} newText={content} />
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
                <Label>Motivo del cambio (para el historial de versiones)</Label>
                <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button disabled={!valid || busy} onClick={handleSubmit}>
            {busy ? "Guardando..." : "Guardar y re-ingerir"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
