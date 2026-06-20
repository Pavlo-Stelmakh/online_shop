import { apiUrl } from "@/lib/api";
import type { CartItem } from "@/types";

type CustomerProfileResponse = {
  id: number;
};

export type CreateOrderResponse = {
  id: number;
  customer_id: number;
  status: string;
  total_price: number;
  total_price_amount?: string;
};

type ApiErrorResponse = {
  detail?: string;
};

async function parseErrorMessage(response: Response, fallback: string) {
  try {
    const data = (await response.json()) as ApiErrorResponse;
    return data.detail || fallback;
  } catch {
    return fallback;
  }
}

async function fetchMyCustomerProfile(accessToken: string) {
  const response = await fetch(apiUrl("/customers/me"), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Не вдалося отримати профіль покупця."));
  }

  return (await response.json()) as CustomerProfileResponse;
}

export async function createOrderFromCart(cart: CartItem[], accessToken: string) {
  const customer = await fetchMyCustomerProfile(accessToken);

  const response = await fetch(apiUrl("/orders"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      customer_id: customer.id,
      items: cart.map((item) => ({
        product_id: item.id,
        quantity: item.quantity,
      })),
    }),
  });

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response, "Не вдалося створити замовлення."));
  }

  return (await response.json()) as CreateOrderResponse;
}
