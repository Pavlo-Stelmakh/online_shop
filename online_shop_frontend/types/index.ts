export type RawProduct = {
  id: unknown;
  name?: unknown;
  price: unknown;
  price_amount?: unknown;
  description?: unknown;
  image_url?: unknown;
  stock: unknown;
  category_id?: unknown;
};

export type Product = {
  id: number;
  name: string;
  price: number;
  priceAmount?: string;
  description: string;
  imageUrl: string | null;
  stock: number;
  categoryId?: number;
};

export type ProductListResponse = {
  items: RawProduct[];
  total: number;
  skip: number;
  limit: number;
  sort_by: string | null;
  sort_order: string;
};

export type TokenResponse = { access_token: string; token_type: string };

export type CartItem = {
  productId: number;
  name: string;
  description: string;
  unitPrice: number;
  priceAmount?: string;
  imageUrl: string | null;
  stock: number;
  quantity: number;
};
