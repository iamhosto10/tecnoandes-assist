import { diffWords } from "diff";

export function DiffView({ oldText, newText }: { oldText: string; newText: string }) {
  const parts = diffWords(oldText, newText);

  if (parts.length === 1 && !parts[0].added && !parts[0].removed) {
    return <p className="text-xs text-muted-foreground">Sin cambios.</p>;
  }

  return (
    <pre className="whitespace-pre-wrap rounded-md border bg-muted/30 p-3 font-mono text-xs leading-relaxed">
      {parts.map((part, index) => (
        <span
          key={index}
          className={
            part.added
              ? "bg-emerald-200/60 text-emerald-900 dark:bg-emerald-900/50 dark:text-emerald-200"
              : part.removed
                ? "bg-red-200/60 text-red-900 line-through dark:bg-red-900/50 dark:text-red-200"
                : undefined
          }
        >
          {part.value}
        </span>
      ))}
    </pre>
  );
}
