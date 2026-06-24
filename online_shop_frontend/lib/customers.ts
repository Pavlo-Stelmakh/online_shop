import { getAuthToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type CustomerProfile = {
  id: number;
  user_id: number;
  name: string;
  email: string;
  phone: string;
};

export async function getMyCustomerProfile(): Promise<CustomerProfile> {
  const token = getAuthToken();

  if (!token) {
    throw new Error("Потрібно увійти перед оформленням замовлення");
  }

  const response = await fetch(`${API_URL}/customers/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Не вдалося отримати профіль покупця");
  }

  return (await response.json()) as CustomerProfile;
}