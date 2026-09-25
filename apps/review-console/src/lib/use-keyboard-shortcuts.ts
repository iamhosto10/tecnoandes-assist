"use client";

import { useEffect } from "react";

type ShortcutMap = Record<string, () => void>;

/** Atajos de una tecla (a, e, d, j, k, ?...). Se desactivan mientras el
 * foco está en un campo de texto, para no interferir con escribir. */
export function useKeyboardShortcuts(map: ShortcutMap, enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;

      const handler = map[event.key.toLowerCase()];
      if (handler) {
        event.preventDefault();
        handler();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [enabled, map]);
}
