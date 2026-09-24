"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { ApiError } from "@tecnoandes/api-client";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Header } from "./header";
import { SuggestedQuestions } from "./suggested-questions";
import { ChatMessageView, type ChatEntry } from "./chat-message";

function newId() {
  return crypto.randomUUID();
}

export function ChatApp() {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [transparentMode, setTransparentMode] = useState(false);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, loading]);

  async function sendQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setEntries((prev) => [...prev, { id: newId(), role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const response = await api.ask(trimmed);
      setEntries((prev) => [...prev, { id: newId(), role: "assistant", response }]);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? `No se pudo contactar al asistente (${error.status}). Intenta de nuevo.`
          : "No se pudo contactar al asistente. Revisa tu conexión e intenta de nuevo.";
      setEntries((prev) => [...prev, { id: newId(), role: "assistant-error", content: message }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-dvh flex-col">
      <Header transparentMode={transparentMode} onTransparentModeChange={setTransparentMode} />

      <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {entries.length === 0 && (
            <div className="space-y-3 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              <p>
                Hola, soy el asistente de TecnoAndes. Pregúntame sobre productos, sedes,
                garantías, envíos o pedidos.
              </p>
              <SuggestedQuestions onSelect={sendQuestion} disabled={loading} />
            </div>
          )}

          {entries.map((entry) => (
            <ChatMessageView key={entry.id} entry={entry} transparentMode={transparentMode} />
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="w-48 space-y-2 rounded-2xl rounded-bl-sm border bg-card px-4 py-3">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-3/4" />
              </div>
            </div>
          )}

          <div ref={scrollAnchorRef} />
        </div>
      </div>

      <form
        className="border-t bg-background px-4 py-3 sm:px-6"
        onSubmit={(event) => {
          event.preventDefault();
          void sendQuestion(input);
        }}
      >
        <div className="mx-auto flex max-w-2xl items-center gap-2">
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Escribe tu pregunta..."
            disabled={loading}
            autoFocus
          />
          <Button type="submit" size="icon" disabled={loading || !input.trim()}>
            <Send className="size-4" />
            <span className="sr-only">Enviar</span>
          </Button>
        </div>
      </form>
    </div>
  );
}
