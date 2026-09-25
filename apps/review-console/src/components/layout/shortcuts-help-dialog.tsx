"use client";

import { useState } from "react";
import { CircleHelp } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useKeyboardShortcuts } from "@/lib/use-keyboard-shortcuts";

const SHORTCUTS: Array<[string, string]> = [
  ["A", "Aprobar el caso actual"],
  ["E", "Escalar el caso actual (pide una nota)"],
  ["D", "Descartar el caso actual"],
  ["J", "Ir al caso siguiente"],
  ["K", "Ir al caso anterior"],
  ["?", "Mostrar esta ayuda"],
];

export function ShortcutsHelpDialog() {
  const [open, setOpen] = useState(false);
  useKeyboardShortcuts({ "?": () => setOpen(true) });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label="Atajos de teclado">
            <CircleHelp className="size-4" />
          </Button>
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Atajos de teclado</DialogTitle>
        </DialogHeader>
        <dl className="space-y-2 text-sm">
          {SHORTCUTS.map(([key, label]) => (
            <div key={key} className="flex items-center gap-3">
              <kbd className="flex h-6 min-w-6 items-center justify-center rounded border bg-muted px-1.5 font-mono text-xs">
                {key}
              </kbd>
              <dd className="text-muted-foreground">{label}</dd>
            </div>
          ))}
        </dl>
        <p className="text-xs text-muted-foreground">
          A/E/D actúan sobre el caso abierto — funcionan en el detalle, no en la cola.
        </p>
      </DialogContent>
    </Dialog>
  );
}
