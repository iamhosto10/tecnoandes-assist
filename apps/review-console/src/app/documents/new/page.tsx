"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { ApiError } from "@tecnoandes/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/auth-context";

function NewDocumentForm() {
  const { api } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  // Llega desde "Crear documento" en /gaps — precarga el título/contenido
  // con la pregunta representativa del grupo, para no partir de cero.
  const hint = searchParams.get("hint") ?? "";

  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState(hint);
  const [category, setCategory] = useState("faq");
  const [content, setContent] = useState(hint ? `## ${hint}\n\n` : "");
  const [saving, setSaving] = useState(false);

  const valid = slug.trim() && title.trim() && category.trim() && content.trim();

  async function handleSubmit() {
    setSaving(true);
    try {
      const doc = await api.createDocument({ slug, title, category, content });
      toast.success("Documento creado e ingerido");
      router.push(`/documents/${doc.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast.error("Ya existe un documento con ese slug");
      } else {
        toast.error("No se pudo crear el documento");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 px-4 py-6 sm:px-6">
      <h1 className="text-lg font-semibold">Nuevo documento</h1>
      {hint && (
        <p className="rounded-md border border-dashed bg-muted/30 p-2 text-xs text-muted-foreground">
          Precargado desde una brecha de conocimiento: &quot;{hint}&quot;
        </p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>Slug</Label>
          <Input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="productos-x"
          />
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
        <Textarea
          rows={12}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="font-mono text-xs"
        />
      </div>

      <Button disabled={!valid || saving} onClick={handleSubmit}>
        {saving ? "Creando..." : "Crear e ingerir"}
      </Button>
    </div>
  );
}

export default function NewDocumentPage() {
  return (
    <Suspense>
      <NewDocumentForm />
    </Suspense>
  );
}
