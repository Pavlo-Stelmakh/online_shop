export type ApiProduct = {
  id: number | string;
  name: string;
  price?: number | string | null;
  price_amount?: number | string | null;
  description?: string | null;
  image_url?: string | null;
  stock?: number | string | null;
  low_stock_threshold?: number | string | null;
  category_id?: number | string | null;
  category?: unknown;
};

export type ProductsEnvelope = {
  items: ApiProduct[];
  total: number;
  skip: number;
  limit: number;
  sort_by: string;
  sort_order: string;
};

export type Product = {
  id: number;
  name: string;
  description: string;
  price: number;
  imageUrl: string | null;
  stock: number;
};

export type CartItem = Product & {
  quantity: number;
};
