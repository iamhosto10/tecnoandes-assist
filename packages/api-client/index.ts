import type { components } from "./types.js";

// Tipos re-exportados desde el OpenAPI del backend (types.ts es generado,
// no se edita a mano — ver `pnpm generate`). Así el chat y la consola de
// revisión comparten el mismo contrato sin duplicar interfaces.
export type AskRequest = components["schemas"]["AskRequest"];
export type AskResponse = components["schemas"]["AskResponse"];
export type SourceChunk = components["schemas"]["SourceChunk"];
export type ConfidenceBreakdown = components["schemas"]["ConfidenceBreakdown"];
export type ScoreBreakdown = components["schemas"]["ScoreBreakdown"];
export type ScoreComponent = components["schemas"]["ScoreComponentOut"];

// Derivado del schema real (ahora un enum de verdad en el OpenAPI) en vez
// de redeclararlo a mano, para que no se puedan desincronizar.
export type Decision = AskResponse["decision"];

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiClientOptions {
  baseUrl: string;
  reviewToken?: string;
}

export function createApiClient({ baseUrl, reviewToken }: ApiClientOptions) {
  async function request<T>(
    path: string,
    init: RequestInit = {},
  ): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    if (reviewToken) {
      headers.set("Authorization", `Bearer ${reviewToken}`);
    }

    const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
    if (!response.ok) {
      const body = await response.text();
      throw new ApiError(
        `${init.method ?? "GET"} ${path} -> ${response.status}: ${body}`,
        response.status,
      );
    }
    return (await response.json()) as T;
  }

  return {
    ask(question: string): Promise<AskResponse> {
      return request<AskResponse>("/ask", {
        method: "POST",
        body: JSON.stringify({ question } satisfies AskRequest),
      });
    },
  };
}
