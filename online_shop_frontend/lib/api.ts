import type { Product, ProductsResponse, RawProduct } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  return fallback;
}

function normalizeProduct(raw: RawProduct): Product | null {
  const id = toNumber(raw.id, 0);

  if (id <= 0) {
    return null;
  }

  return {
    id,
    name: raw.name || "Без назви",
    description: raw.description || "",
    price: toNumber(raw.price_amount ?? raw.price, 0),
    stock: toNumber(raw.stock, 0),
    categoryId: raw.category_id == null ? null : toNumber(raw.category_id, 0),
    categoryName: raw.category_name || "Без категорії",
  };
}

function extractProducts(data: ProductsResponse): RawProduct[] {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data.items)) {
    return data.items;
  }

  if (Array.isArray(data.products)) {
    return data.products;
  }

  return [];
}

export async function getProducts(): Promise<Product[]> {
  const response = await fetch(`${API_URL}/products`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Не вдалося завантажити товари");
  }

  const data = (await response.json()) as ProductsResponse;

  return extractProducts(data)
    .map(normalizeProduct)
    .filter((product): product is Product => product !== null);
}