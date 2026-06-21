export type Product = {
  id: number;
  name: string;
  price: number;
  price_amount: string;
  description: string;
  image_url: string | null;
  stock: number;
  low_stock_threshold: number;
  category_id: number;
};

type ProductCatalogResponse = {
  items: Product[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getProducts(): Promise<Product[]> {
  const response = await fetch(`${API_BASE_URL}/products/catalog`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Не вдалося завантажити каталог товарів.");
  }

  const catalog = (await response.json()) as ProductCatalogResponse;

  return catalog.items;
}
