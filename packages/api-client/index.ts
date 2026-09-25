import type { components, operations } from "./types.js";

// Tipos re-exportados desde el OpenAPI del backend (types.ts es generado,
// no se edita a mano — ver `pnpm generate`). Así el chat y la consola de
// revisión comparten el mismo contrato sin duplicar interfaces.
export type AskRequest = components["schemas"]["AskRequest"];
export type AskResponse = components["schemas"]["AskResponse"];
export type SourceChunk = components["schemas"]["SourceChunk"];
export type ConfidenceBreakdown = components["schemas"]["ConfidenceBreakdown"];
export type ScoreBreakdown = components["schemas"]["ScoreBreakdown"];
export type ScoreComponent = components["schemas"]["ScoreComponentOut"];

export type ReviewItemSummary = components["schemas"]["ReviewItemSummary"];
export type ReviewItemListResponse = components["schemas"]["ReviewItemListResponse"];
export type ReviewItemDetail = components["schemas"]["ReviewItemDetail"];
export type ReviewAction = components["schemas"]["ReviewActionOut"];
export type ReviewActionRequest = components["schemas"]["ReviewActionRequest"];
export type ActionType = components["schemas"]["ReviewActionRequest"]["action_type"];
export type RetestResponse = components["schemas"]["RetestResponse"];
export type KnowledgeGapGroup = components["schemas"]["KnowledgeGapGroup"];

export type DocumentSummary = components["schemas"]["DocumentSummary"];
export type DocumentDetail = components["schemas"]["DocumentDetail"];
export type DocumentVersion = components["schemas"]["DocumentVersionOut"];
export type DocumentCreateRequest = components["schemas"]["DocumentCreateRequest"];
export type DocumentUpdateRequest = components["schemas"]["DocumentUpdateRequest"];

export type ReviewItemFilters = operations["get_review_items_review_items_get"]["parameters"]["query"];

// Derivado del schema real (ahora un enum de verdad en el OpenAPI) en vez
// de redeclararlo a mano, para que no se puedan desincronizar.
export type Decision = AskResponse["decision"];
export type ReviewStatus = ReviewItemSummary["status"];
export type RuleApplied = AskResponse["rule_applied"];

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

function toQueryString(params: Record<string, unknown> | undefined): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function createApiClient({ baseUrl, reviewToken }: ApiClientOptions) {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
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

    getReviewItems(filters: ReviewItemFilters = {}): Promise<ReviewItemListResponse> {
      return request<ReviewItemListResponse>(`/review/items${toQueryString(filters)}`);
    },

    getReviewItem(id: number): Promise<ReviewItemDetail> {
      return request<ReviewItemDetail>(`/review/items/${id}`);
    },

    postReviewAction(id: number, body: ReviewActionRequest): Promise<ReviewItemDetail> {
      return request<ReviewItemDetail>(`/review/items/${id}/actions`, {
        method: "POST",
        body: JSON.stringify(body),
      });
    },

    retestReviewItem(id: number): Promise<RetestResponse> {
      return request<RetestResponse>(`/review/items/${id}/retest`, { method: "POST" });
    },

    getKnowledgeGaps(minGroupSize = 2): Promise<KnowledgeGapGroup[]> {
      return request<KnowledgeGapGroup[]>(
        `/review/knowledge-gaps${toQueryString({ min_group_size: minGroupSize })}`,
      );
    },

    getDocuments(params: { q?: string; category?: string } = {}): Promise<{
      items: DocumentSummary[];
    }> {
      return request(`/documents${toQueryString(params)}`);
    },

    getDocument(id: number): Promise<DocumentDetail> {
      return request<DocumentDetail>(`/documents/${id}`);
    },

    createDocument(body: DocumentCreateRequest): Promise<DocumentDetail> {
      return request<DocumentDetail>("/documents", {
        method: "POST",
        body: JSON.stringify(body),
      });
    },

    updateDocument(id: number, body: DocumentUpdateRequest): Promise<DocumentDetail> {
      return request<DocumentDetail>(`/documents/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
    },
  };
}
