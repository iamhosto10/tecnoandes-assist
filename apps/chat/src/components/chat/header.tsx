"use client";

import { Mountain } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export function Header({
  transparentMode,
  onTransparentModeChange,
}: {
  transparentMode: boolean;
  onTransparentModeChange: (value: boolean) => void;
}) {
  return (
    <header className="flex items-center justify-between border-b bg-background px-4 py-3 sm:px-6">
      <div className="flex items-center gap-2">
        <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Mountain className="size-4.5" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-none">TecnoAndes</p>
          <p className="text-xs text-muted-foreground">Asistente de atención al cliente</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Label htmlFor="transparent-mode" className="text-xs text-muted-foreground">
          Modo transparente
        </Label>
        <Switch
          id="transparent-mode"
          checked={transparentMode}
          onCheckedChange={onTransparentModeChange}
        />
      </div>
    </header>
  );
}
