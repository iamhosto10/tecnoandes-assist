import { createApiClient } from "@tecnoandes/api-client";

// Público a propósito: /ask no requiere auth (lo usa el chat del cliente).
// El puerto por defecto coincide con docker-compose.yml sin necesitar un
// .env.local para desarrollo local.
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = createApiClient({ baseUrl: API_BASE_URL });
