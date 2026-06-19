import type { Customer, Order, OrderItemPayload, Product, ProductListResponse, TokenResponse, User } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://online-shop-api-z9y4.onrender.com";

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown; token?: string | null };

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function parseResponse(response: Response) {
  const text = await response.text();
  if (!text) return null;
  try { return JSON.parse(text); } catch { return text; }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      body: options.body instanceof FormData ? options.body : options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    throw new ApiError("Сервер тимчасово недоступний. Спробуйте пізніше.", 0, error);
  }

  const data = await parseResponse(response);
  if (!response.ok) {
    const detail = typeof data === "object" && data && "detail" in data ? (data as { detail: unknown }).detail : undefined;
    const message = typeof detail === "string" ? detail : "Не вдалося виконати запит. Перевірте дані та спробуйте ще раз.";
    throw new ApiError(message, response.status, data);
  }
  return data as T;
}

export const api = {
  getProducts: () => apiRequest<ProductListResponse>("/products?limit=100&sort_by=id&sort_order=desc"),
  getProduct: (id: number) => apiRequest<Product>(`/products/${id}`),
  register: (body: { username: string; email: string; password: string }) => apiRequest<User>("/auth/register", { method: "POST", body }),
  login: (username: string, password: string) => {
    const form = new FormData();
    form.set("username", username);
    form.set("password", password);
    return apiRequest<TokenResponse>("/auth/login", { method: "POST", body: form });
  },
  me: (token: string) => apiRequest<User>("/auth/me", { token }),
  getMyCustomer: (token: string) => apiRequest<Customer>("/customers/me", { token }),
  createCustomer: (token: string, body: { name: string; email: string; phone: string }) => apiRequest<Customer>("/customers", { method: "POST", token, body }),
  createOrder: (token: string, customerId: number, items: OrderItemPayload[]) => apiRequest<Order>("/orders", { method: "POST", token, body: { customer_id: customerId, items } }),
};
