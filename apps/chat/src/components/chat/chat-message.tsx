import type { AskResponse } from "@tecnoandes/api-client";
import { cn } from "@/lib/utils";
import { DecisionBanner } from "./decision-banner";
import { SourcesList } from "./sources-list";
import { TransparentPanel } from "./transparent-panel";

export type ChatEntry =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; response: AskResponse }
  | { id: string; role: "assistant-error"; content: string };

export function ChatMessageView({
  entry,
  transparentMode,
}: {
  entry: ChatEntry;
  transparentMode: boolean;
}) {
  if (entry.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-sm text-primary-foreground">
          {entry.content}
        </div>
      </div>
    );
  }

  if (entry.role === "assistant-error") {
    return (
      <div className="flex justify-start">
        <div className="max-w-[80%] rounded-2xl rounded-bl-sm border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {entry.content}
        </div>
      </div>
    );
  }

  const { response } = entry;

  return (
    <div className="flex justify-start">
      <div
        className={cn(
          "max-w-[85%] space-y-2 rounded-2xl rounded-bl-sm border bg-card px-4 py-3 text-sm text-card-foreground",
        )}
      >
        <DecisionBanner decision={response.decision} />
        <p className="whitespace-pre-wrap">{response.answer}</p>
        <SourcesList sources={response.sources} />
        {transparentMode && <TransparentPanel response={response} />}
      </div>
    </div>
  );
}
