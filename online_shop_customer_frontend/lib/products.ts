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
type ProductResponse = Product | { item: Product } | { product: Product };

function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function isProduct(data: unknown): data is Product {
  if (!data || typeof data !== "object") {
    return false;
  }

  const candidate = data as Partial<Product>;

  return typeof candidate.id === "number" && typeof candidate.name === "string";
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


function parseProductResponse(data: ProductResponse): Product {
  if (isProduct(data)) {
    return data;
  }

  if (data && typeof data === "object") {
    const candidate = data as { item?: unknown; product?: unknown };

    if (isProduct(candidate.item)) {
      return candidate.item;
    }

    if (isProduct(candidate.product)) {
      return candidate.product;
    }
  }

  throw new Error("Unexpected product response format.");
}

export async function getProduct(productId: number): Promise<Product | null> {
  const productUrl = `${getApiBaseUrl()}/products/${productId}`;

  try {
    const response = await fetch(productUrl, { cache: "no-store" });

    if (response.ok) {
      const data = (await response.json()) as ProductResponse;
      return parseProductResponse(data);
    }

    if (response.status !== 404) {
      console.warn(`Failed to fetch product by id: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown network error";
    console.warn(`Failed to fetch product by id: ${message}`);
  }

  const products = await getProducts();

  return products.find((product) => product.id === productId) ?? null;
}
