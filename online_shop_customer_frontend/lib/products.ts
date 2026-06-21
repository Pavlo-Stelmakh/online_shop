export type Product = {
  id: number;
  name: string;
  price: number;
  price_amount?: string;
  description: string;
  image_url?: string | null;
  stock: number;
  category_id?: number;
};

type ProductsResponse = Product[] | { items: Product[] };

const DEFAULT_API_BASE_URL = "https://online-shop-api-z9y4.onrender.com";

function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

function extractProducts(data: ProductsResponse): Product[] {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data.items)) {
    return data.items;
  }

  throw new Error("Неправильний формат відповіді каталогу товарів.");
}

export async function getProducts(): Promise<Product[]> {
  const productsUrl = `${getApiBaseUrl()}/products`;

  let response: Response;

  try {
    response = await fetch(productsUrl, {
      method: "GET",
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(
      `Не вдалося отримати каталог товарів: ${error instanceof Error ? error.message : "fetch failed"}`,
    );
  }

  if (!response.ok) {
    throw new Error(`Не вдалося отримати каталог товарів: HTTP ${response.status}`);
  }

  const data = (await response.json()) as ProductsResponse;
  return extractProducts(data);
}
