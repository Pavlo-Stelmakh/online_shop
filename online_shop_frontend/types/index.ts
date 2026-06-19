export type Category = { id: number; name: string };

export type Product = {
  id: number;
  name: string;
  price: number;
  price_amount?: string;
  description: string;
  image_url?: string | null;
  stock: number;
  low_stock_threshold?: number;
  category_id?: number;
  category?: Category;
};

export type ProductListResponse = {
  items: Product[];
  total: number;
  skip: number;
  limit: number;
  sort_by: string | null;
  sort_order: string;
};

export type User = { id: number; username: string; email: string; role: string };
export type TokenResponse = { access_token: string; token_type: string };
export type Customer = { id: number; user_id: number; name: string; email: string; phone: string };
export type OrderItemPayload = { product_id: number; quantity: number };
export type Order = { id: number; customer_id: number; status: string; total_price: number; total_price_amount?: string };

export type CartItem = {
  productId: number;
  name: string;
  unitPrice: number;
  priceAmount?: string;
  imageUrl?: string | null;
  stock?: number;
  quantity: number;
};
