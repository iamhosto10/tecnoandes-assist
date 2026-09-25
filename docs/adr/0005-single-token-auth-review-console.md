# 0005 — Auth de un solo token compartido para la consola de revisión

## Estado

Aceptado (Fase 0, implementado en Fase 3). **Explícitamente no apto para
producción tal cual** — ver Consecuencias.

## Contexto

`/review`, `/documents` y `/metrics` necesitan estar protegidos (no son
públicos como `/ask`), pero el proyecto es una demo de portafolio con un
único "revisor" real: no hay múltiples usuarios, roles, ni necesidad de
saber "cuál humano" hizo cada acción más allá de lo que ya escribe a mano
en el campo `actor` de cada `ReviewAction`.

## Decisión

Un solo token compartido, `REVIEW_CONSOLE_TOKEN`, leído de `.env`,
verificado con un simple `Header == f"Bearer {token}"`
(`app/core/security.py`). Sin tabla de usuarios, sin sesiones, sin OAuth.

## Consecuencias

- Cero infraestructura extra (no hay proveedor de identidad, no hay tabla
  `users`) — apropiado para el alcance de la demo.
- **No aísla quién hizo qué**: `actor` en `review_actions` es un campo de
  texto libre que el revisor escribe a mano, no una identidad verificada.
  Cualquiera con el token puede actuar como cualquier "actor".
- **No apto para producción**: en un entorno real, esto sería sesiones
  por usuario (OAuth/SSO) con roles (revisor / admin) y `actor` derivado
  de la sesión autenticada, no de un campo de texto.

## Alternativas consideradas

- **OAuth/SSO con roles reales.** La opción correcta para producción;
  descartada para esta demo por ser infraestructura que no aporta a lo
  que el proyecto busca demostrar (RAG con confianza + human-in-the-loop),
  y que sí agregaría superficie de configuración (proveedor de identidad,
  gestión de usuarios) fuera del alcance de un portafolio.
