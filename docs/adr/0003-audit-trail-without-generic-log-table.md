# 0003 — Auditoría sin una tabla `audit_log` genérica

## Estado

Aceptado (Fase 0, reforzado en Fase 3).

## Contexto

El diseño pide poder reconstruir "qué pasó" con cualquier caso: qué
preguntó el cliente, qué señales tuvo, qué decidió el sistema, qué hizo el
revisor, y cómo cambió un documento. El patrón común para esto es una
tabla `audit_log` polimórfica (`entity_type`, `entity_id`, `action`,
`payload` jsonb).

## Decisión

No hay una tabla de auditoría genérica. La trazabilidad sale de tres
tablas de dominio, cada una ya necesaria por otra razón:

- `queries`: un registro inmutable de cada `/ask`, con todas las señales
  de confianza y la decisión — no solo "qué contestó", sino "por qué".
- `document_versions`: el contenido anterior de un documento antes de
  cada edición, con quién y por qué lo cambió.
- `review_actions`: el historial de acciones del revisor sobre un caso.

## Consecuencias

- Cada tabla es fácil de consultar con SQL normal y columnas tipadas — sin
  parsear un `payload jsonb` genérico ni un `entity_type` que hay que
  interpretar según el caso.
- El costo es que "todo lo que pasó" no vive en un solo lugar: reconstruir
  la historia completa de un caso implica un JOIN entre `queries` ->
  `review_items` -> `review_actions`, y por separado `document_versions`
  si hubo una edición. Para el tamaño de esta demo (cientos/miles de
  filas) no es un problema real.

## Alternativas consideradas

- **Tabla `audit_log` polimórfica.** Un solo lugar para "todo lo que
  pasó", pero más difícil de consultar bien (índices sobre un jsonb
  genérico, sin garantías de esquema por tipo de evento) y con el mismo
  contenido que ya vive, tipado, en las tres tablas de arriba.
