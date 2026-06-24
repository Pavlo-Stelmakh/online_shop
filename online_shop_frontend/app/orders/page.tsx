"use client";

import { useState } from "react";
import Header from "@/components/Header";
import { getMyOrders, type MyOrder } from "@/lib/orders";

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("uk-UA");
}

function getOrderTotal(order: MyOrder): string {
  if (order.total_price_amount) {
    return order.total_price_amount;
  }

  return order.total_price.toFixed(2);
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<MyOrder[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleLoadOrders() {
    setErrorMessage("");
    setIsLoading(true);

    try {
      const data = await getMyOrders();
      setOrders(data);
      setIsLoaded(true);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Не вдалося завантажити замовлення"
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <Header
          title="Мої замовлення"
          description="Перегляд замовлень поточного покупця."
        />

        <div className="mb-6">
          <button
            type="button"
            onClick={handleLoadOrders}
            disabled={isLoading}
            className="rounded-lg bg-black px-4 py-2 text-white disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            {isLoading ? "Завантаження..." : "Завантажити замовлення"}
          </button>
        </div>

        {errorMessage && (
          <p className="mb-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {errorMessage}
          </p>
        )}

        {isLoaded && orders.length === 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-gray-700">
            Замовлень поки немає.
          </div>
        )}

        {orders.length > 0 && (
          <section className="space-y-4">
            {orders.map((order) => (
              <article
                key={order.id}
                className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">
                      Замовлення #{order.id}
                    </h2>
                    <p className="mt-1 text-sm text-gray-500">
                      Створено: {formatDate(order.created_at)}
                    </p>
                  </div>

                  <div className="text-left sm:text-right">
                    <p className="text-sm text-gray-500">Статус</p>
                    <p className="font-semibold text-gray-900">{order.status}</p>
                  </div>
                </div>

                <div className="mt-4 border-t border-gray-100 pt-4">
                  <p className="font-semibold text-gray-900">
                    Сума: {getOrderTotal(order)} грн
                  </p>
                  <p className="mt-1 text-sm text-gray-600">
                    Позицій у замовленні: {order.items.length}
                  </p>
                </div>

                {order.items.length > 0 && (
                  <div className="mt-4 rounded-lg bg-gray-50 p-4">
                    <p className="mb-2 text-sm font-medium text-gray-700">
                      Товари:
                    </p>

                    <ul className="space-y-2">
                      {order.items.map((item) => (
                        <li
                          key={item.id}
                          className="flex items-center justify-between gap-4 text-sm text-gray-700"
                        >
                          <span>Product ID: {item.product_id}</span>
                          <span>Кількість: {item.quantity}</span>
                          <span>Ціна: {item.unit_price.toFixed(2)} грн</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </article>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}