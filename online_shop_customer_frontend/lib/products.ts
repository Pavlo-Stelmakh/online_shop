export type Product = {
  id: number;
  name: string;
  description: string;
  price: number;
  price_amount?: string;
  image_url?: string | null;
  stock: number;
};

const DEFAULT_API_BASE_URL = "https://online-shop-api-z9y4.onrender.com";

type ProductsResponse = Product[] | { items: Product[] };

function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function parseProductsResponse(data: ProductsResponse): Product[] {
  if (Array.isArray(data)) {
    return data;
  }

  if (data && Array.isArray(data.items)) {
    return data.items;
  }

  throw new Error("Unexpected products response format.");
}

export async function getProducts(): Promise<Product[]> {
  const productsUrl = `${getApiBaseUrl()}/products`;

  let response: Response;

  try {
    response = await fetch(productsUrl, { cache: "no-store" });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown network error";
    throw new Error(`Failed to fetch products: ${message}`);
  }

  if (!response.ok) {
    throw new Error(`Failed to fetch products: ${response.status} ${response.statusText}`);
  }

  const data = (await response.json()) as ProductsResponse;
  return parseProductsResponse(data);
}
