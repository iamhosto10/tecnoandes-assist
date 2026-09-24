"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { SourceChunk } from "@tecnoandes/api-client";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function SourcesList({ sources }: { sources: SourceChunk[] }) {
  const [open, setOpen] = useState(false);

  if (sources.length === 0) return null;

  const citedCount = sources.filter((s) => s.cited).length;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
        <ChevronDown
          className={cn("size-3.5 transition-transform", open && "rotate-180")}
        />
        Fuentes ({citedCount > 0 ? `${citedCount} citadas` : sources.length})
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2 space-y-2">
        {sources.map((source) => (
          <div
            key={source.chunk_id}
            className={cn(
              "rounded-md border px-3 py-2 text-xs",
              source.cited ? "border-primary/30 bg-accent/50" : "border-border",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{source.document_title}</span>
              {source.cited && (
                <Badge variant="secondary" className="text-[10px]">
                  citado
                </Badge>
              )}
            </div>
            {source.heading_path && (
              <p className="text-muted-foreground">{source.heading_path}</p>
            )}
            <p className="mt-1 text-foreground/80">{source.content}</p>
          </div>
        ))}
      </CollapsibleContent>
    </Collapsible>
  );
}
