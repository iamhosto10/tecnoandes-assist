# apps/review-console

Consola de revisión de TecnoAndes Assist (Next.js App Router). Ver el
[`CLAUDE.md`](../../CLAUDE.md) de la raíz del repo para el contexto completo
del proyecto.

## Desarrollo

```bash
# desde la raíz del repo
make review-console
```

Corre en `localhost:3001` (el chat usa `3000`). Necesita el backend en
`localhost:8000` (`make up` desde la raíz) y el token de
`REVIEW_CONSOLE_TOKEN` (`.env` en la raíz) para iniciar sesión.
