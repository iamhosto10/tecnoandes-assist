"use client";

import { Button } from "@/components/ui/button";

// Una por categoría de la Fase 12 del diseño: respuesta directa, parcial
// (el catálogo no tiene el dato exacto), fuera de la base, y un reclamo
// que debe escalarse — así una sola tanda de clics muestra las cuatro
// rutas de confianza en la demo.
const SUGGESTIONS = [
  "¿Cuánto cuesta el iPhone 13?",
  "¿El Samsung Galaxy S23 viene en color azul?",
  "¿Venden bicicletas?",
  "Me cobraron dos veces, ¿qué hago?",
];

export function SuggestedQuestions({
  onSelect,
  disabled,
}: {
  onSelect: (question: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {SUGGESTIONS.map((question) => (
        <Button
          key={question}
          type="button"
          variant="outline"
          size="sm"
          className="rounded-full"
          disabled={disabled}
          onClick={() => onSelect(question)}
        >
          {question}
        </Button>
      ))}
    </div>
  );
}
