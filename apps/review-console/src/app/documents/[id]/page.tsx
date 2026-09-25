"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { ApiError, type DocumentDetail } from "@tecnoandes/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DiffView } from "@/components/shared/diff-view";
import { useAuth } from "@/lib/auth-context";
import { useApiResource } from "@/lib/use-api-resource";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);

  const {
    data: doc,
    loading,
    reload,
  } = useApiResource((api) => api.getDocument(documentId), [documentId]);

  if (loading || !doc) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // `key` fuerza un remount limpio si se navega a otro documento — así el
  // estado del editor siempre arranca de las props, sin sincronizarlo con
  // un efecto (ver docs de React: "you might not need an effect").
  return <DocumentEditor key={doc.id} doc={doc} onSaved={reload} />;
}

function DocumentEditor({ doc, onSaved }: { doc: DocumentDetail; onSaved: () => void }) {
  const { api } = useAuth();
  const [content, setContent] = useState(doc.content);
  const [changedBy, setChangedBy] = useState("reviewer");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateDocument(doc.id, {
        content,
        changed_by: changedBy,
        reason: reason || "Edición manual desde la consola",
      });
      setLastSavedAt(new Date());
      toast.success("Guardado y re-ingerido");
      setReason("");
      onSaved();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  const hasChanges = content !== doc.content;

  // Versions vienen del backend de más nueva a más vieja; para diffear
  // cada edición contra lo que quedó DESPUÉS de ella hace falta el orden
  // cronológico (ascendente).
  const versionsAscending = [...doc.versions].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-lg font-semibold">{doc.title}</h1>
        <p className="text-xs text-muted-foreground">
          {doc.slug} · {doc.category}
        </p>
      </div>

      <Tabs defaultValue="editor">
        <TabsList>
          <TabsTrigger value="editor">Editor</TabsTrigger>
          <TabsTrigger value="history">
            Historial de versiones ({doc.versions.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="editor" className="space-y-3">
          <Textarea
            rows={16}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="font-mono text-xs"
          />

          {hasChanges && (
            <div className="space-y-1.5">
              <Label>Vista de diferencias (sin guardar)</Label>
              <DiffView oldText={doc.content} newText={content} />
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Tu nombre</Label>
              <Input value={changedBy} onChange={(e) => setChangedBy(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Motivo del cambio</Label>
              <Input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Ej: agregar colores disponibles"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button disabled={!hasChanges || saving} onClick={handleSave}>
              {saving ? "Guardando y re-ingiriendo..." : "Guardar y re-ingerir"}
            </Button>
            {lastSavedAt && (
              <span className="text-xs text-muted-foreground">
                ✓ Re-ingerido a las {lastSavedAt.toLocaleTimeString("es-CO")}
              </span>
            )}
          </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-3">
          {doc.versions.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Sin ediciones todavía — este documento sigue igual desde la ingesta inicial.
            </p>
          )}
          {[...doc.versions]
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .map((version) => {
              const ascIndex = versionsAscending.findIndex((v) => v.id === version.id);
              const contentAfter = versionsAscending[ascIndex + 1]?.content ?? doc.content;
              return (
                <div key={version.id} className="rounded-lg border bg-card p-3">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      <span className="font-medium text-foreground">{version.changed_by}</span> ·{" "}
                      {new Date(version.created_at).toLocaleString("es-CO")}
                      {version.review_item_id && ` · caso #${version.review_item_id}`}
                    </span>
                  </div>
                  {version.reason && <p className="mt-1 text-sm">{version.reason}</p>}
                  <div className="mt-2">
                    <DiffView oldText={version.content} newText={contentAfter} />
                  </div>
                </div>
              );
            })}
        </TabsContent>
      </Tabs>
    </div>
  );
}
