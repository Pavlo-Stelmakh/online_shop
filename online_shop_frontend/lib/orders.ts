import { getAuthToken } from "@/lib/auth";
import type { CartItem } from "@/lib/cart";
import { getMyCustomerProfile } from "@/lib/customers";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type OrderItemCreate = {
  product_id: number;
  quantity: number;
};

export type OrderCreateRequest = {
  customer_id: number;
  items: OrderItemCreate[];
};

export type OrderResponse = {
  id: number;
  customer_id: number;
  total_price: number;
  status: string;
};

export async function createOrderFromCart(items: CartItem[]): Promise<OrderResponse> {
  const token = getAuthToken();

  if (!token) {
    throw new Error("Потрібно увійти перед оформленням замовлення");
  }

  if (items.length === 0) {
    throw new Error("Кошик порожній");
  }

  const customer = await getMyCustomerProfile();

  const orderPayload: OrderCreateRequest = {
    customer_id: customer.id,
    items: items.map((item) => ({
      product_id: item.product.id,
      quantity: item.quantity,
    })),
  };

  const response = await fetch(`${API_URL}/orders`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(orderPayload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Не вдалося створити замовлення");
  }

  return (await response.json()) as OrderResponse;
}

export type OrderItemResponse = {
  id: number;
  product_id: number;
  quantity: number;
  unit_price: number;
};

export type MyOrder = {
  id: number;
  customer_id: number;
  status: string;
  total_price: number;
  total_price_amount?: string;
  created_at: string;
  items: OrderItemResponse[];
};

export async function getMyOrders(): Promise<MyOrder[]> {
  const token = getAuthToken();

  if (!token) {
    throw new Error("Потрібно увійти, щоб переглянути замовлення");
  }

  const response = await fetch(`${API_URL}/orders/my`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Не вдалося завантажити замовлення: ${response.status} ${errorText}`);
  }

  return (await response.json()) as MyOrder[];
}