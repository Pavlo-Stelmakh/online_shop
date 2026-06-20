import type { Product, RawProduct } from "@/types";

export function normalizeProduct(product: RawProduct): Product {
  const id = Number(product.id);
  const stock = Number(product.stock);
  const price = Number(product.price);
  const priceAmount = typeof product.price_amount === "string" ? product.price_amount : undefined;

  return {
    id,
    stock,
    price,
    priceAmount,
    name: typeof product.name === "string" ? product.name : "Товар без назви",
    description: typeof product.description === "string" ? product.description : "",
    imageUrl: typeof product.image_url === "string" && product.image_url.length > 0 ? product.image_url : null,
    categoryId: product.category_id === undefined || product.category_id === null ? undefined : Number(product.category_id),
  };
}

export function isProductValidForCart(product: Product): boolean {
  return Number.isFinite(product.id) && product.id > 0 && Number.isFinite(product.stock) && product.stock > 0;
}
