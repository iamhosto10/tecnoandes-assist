"use client";

import { useState } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useApiResource } from "@/lib/use-api-resource";

export default function DocumentsPage() {
  const [q, setQ] = useState("");
  const { data, loading } = useApiResource((api) => api.getDocuments({ q: q || undefined }), [q]);

  return (
    <div className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">Base de conocimiento</h1>
        <Link href="/documents/new" className={buttonVariants({ size: "sm" })}>
          + Nuevo documento
        </Link>
      </div>

      <Input
        placeholder="Buscar por título..."
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="max-w-sm"
      />

      <div className="divide-y rounded-lg border bg-card">
        {loading &&
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="p-4">
              <Skeleton className="h-5 w-1/2" />
            </div>
          ))}
        {!loading && data?.items.length === 0 && (
          <p className="p-6 text-center text-sm text-muted-foreground">
            Sin resultados.
          </p>
        )}
        {data?.items.map((doc) => (
          <Link
            key={doc.id}
            href={`/documents/${doc.id}`}
            className="flex items-center justify-between gap-3 p-4 hover:bg-muted/50"
          >
            <div>
              <p className="text-sm font-medium">{doc.title}</p>
              <p className="text-xs text-muted-foreground">{doc.slug}</p>
            </div>
            <Badge variant="secondary">{doc.category}</Badge>
          </Link>
        ))}
      </div>
    </div>
  );
}
