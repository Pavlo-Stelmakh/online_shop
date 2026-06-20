import { apiUrl } from "@/lib/api";
import type { ApiProduct, Product, ProductsEnvelope } from "@/types";

export function normalizeProduct(product: ApiProduct): Product {
  const priceValue = product.price_amount ?? product.price ?? 0;

  return {
    id: Number(product.id),
    name: String(product.name ?? "Без назви"),
    description: String(product.description ?? ""),
    price: Number(priceValue) || 0,
    imageUrl: product.image_url ? String(product.image_url) : null,
    stock: Number(product.stock) || 0,
  };
}

export async function fetchProducts(): Promise<Product[]> {
  const response = await fetch(apiUrl("/products"));

  if (!response.ok) {
    throw new Error("Не вдалося завантажити товари");
  }

  const data = (await response.json()) as ProductsEnvelope;
  return Array.isArray(data.items) ? data.items.map(normalizeProduct) : [];
}
