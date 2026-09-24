import { AlertTriangle, Info, UserRound } from "lucide-react";
import type { Decision } from "@tecnoandes/api-client";
import { cn } from "@/lib/utils";

// El diseño solo pide un aviso explícito para "warn" y "escalate", pero
// "review" (el cliente recibe una respuesta de respaldo, no la del
// modelo) merece el mismo tratamiento — si no, se ve como una respuesta
// floja sin explicación de por qué.
const CONFIG: Record<
  Exclude<Decision, "direct">,
  { icon: typeof AlertTriangle; label: string; className: string }
> = {
  warn: {
    icon: AlertTriangle,
    label:
      "Esta respuesta podría no cubrir tu caso por completo. La estamos revisando.",
    className:
      "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200",
  },
  review: {
    icon: Info,
    label:
      "Todavía no tengo información suficiente para confirmar esto. Un asesor revisará tu consulta.",
    className:
      "border-slate-300 bg-slate-50 text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  },
  escalate: {
    icon: UserRound,
    label: "Un asesor humano se pondrá en contacto contigo pronto.",
    className:
      "border-primary/30 bg-accent text-accent-foreground",
  },
};

export function DecisionBanner({ decision }: { decision: Decision }) {
  if (decision === "direct") return null;

  const { icon: Icon, label, className } = CONFIG[decision];

  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-md border px-3 py-2 text-sm",
        className,
      )}
    >
      <Icon className="mt-0.5 size-4 shrink-0" />
      <span>{label}</span>
    </div>
  );
}
