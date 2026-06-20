import type { ProductListResponse, TokenResponse } from "@/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://online-shop-api-z9y4.onrender.com";

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown };

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseResponse(response: Response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body: options.body instanceof FormData ? options.body : options.body ? JSON.stringify(options.body) : undefined,
  });

  const data = await parseResponse(response);
  if (!response.ok) {
    const detail = typeof data === "object" && data && "detail" in data ? (data as { detail?: unknown }).detail : undefined;
    throw new ApiError(typeof detail === "string" ? detail : "Не вдалося виконати запит.", response.status);
  }

  return data as T;
}

export const api = {
  getProducts: () => apiRequest<ProductListResponse>("/products"),
  register: (body: { username: string; email: string; password: string }) => apiRequest("/auth/register", { method: "POST", body }),
  login: (username: string, password: string) => {
    const form = new FormData();
    form.set("username", username);
    form.set("password", password);
    return apiRequest<TokenResponse>("/auth/login", { method: "POST", body: form });
  },
};
