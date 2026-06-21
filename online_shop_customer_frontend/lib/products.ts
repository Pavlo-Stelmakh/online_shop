export type Product = {
  id?: string | number;
  name?: string;
  description?: string;
  price?: number | string;
  stock?: number | string;
  image_url?: string | null;
};

const DEFAULT_API_BASE_URL = "https://online-shop-api-z9y4.onrender.com";

type ProductsEnvelope = {
  items?: unknown;
  total?: unknown;
  skip?: unknown;
  limit?: unknown;
  sort_by?: unknown;
  sort_order?: unknown;
};

function isProduct(value: unknown): value is Product {
  return typeof value === "object" && value !== null;
}

function normalizeProducts(payload: unknown): Product[] {
  const products = Array.isArray(payload)
    ? payload
    : Array.isArray((payload as ProductsEnvelope | null)?.items)
      ? (payload as ProductsEnvelope).items
      : [];

  return products.filter(isProduct);
}

export async function getProducts(): Promise<Product[]> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  const response = await fetch(`${apiBaseUrl}/products`, {
    headers: {
      Accept: "application/json",
    },
    next: { revalidate: 60 },
  });

  if (!response.ok) {
    throw new Error(`Не вдалося завантажити товари: ${response.status} ${response.statusText}`);
  }

  const payload: unknown = await response.json();
  return normalizeProducts(payload);
}
