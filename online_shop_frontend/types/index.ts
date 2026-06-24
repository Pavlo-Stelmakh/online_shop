export type RawProduct = {
  id: number | string | null;
  name: string;
  description?: string | null;
  price?: number | string | null;
  price_amount?: number | string | null;
  stock?: number | string | null;
  category_id?: number | string | null;
  category_name?: string | null;
};

export type Product = {
  id: number;
  name: string;
  description: string;
  price: number;
  stock: number;
  categoryId: number | null;
  categoryName: string;
};

export type ProductsResponse =
  | RawProduct[]
  | {
      items?: RawProduct[];
      products?: RawProduct[];
    };