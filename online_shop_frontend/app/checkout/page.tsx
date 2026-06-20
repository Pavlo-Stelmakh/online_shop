"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { CartItem } from "@/types";
import { cartTotal, formatPrice, getCart } from "@/lib/cart";
import { getAccessToken } from "@/lib/auth";

export default function CheckoutPage() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setItems(getCart());
    setIsLoggedIn(Boolean(getAccessToken()));
  }, []);

  if (!items.length) {
    return (
      <div className="rounded-xl bg-white p-8 text-center">
        <h1 className="text-2xl font-bold">Кошик порожній</h1>
        <p className="mt-2 text-slate-600">Додайте товари перед оформленням.</p>
        <Link className="mt-4 inline-block rounded bg-blue-600 px-4 py-2 text-white" href="/">
          До каталогу
        </Link>
      </div>
    );
  }

  if (!isLoggedIn) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl bg-white p-8 text-center shadow">
        <h1 className="text-2xl font-bold">Потрібен вхід</h1>
        <p className="mt-3 text-slate-600">Увійдіть в акаунт, щоб оформити замовлення.</p>
        <Link className="mt-4 inline-block rounded bg-blue-600 px-4 py-2 text-white" href="/login">
          Увійти
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <section className="rounded-2xl bg-white p-6 shadow">
        <h1 className="text-2xl font-bold">Оформлення замовлення</h1>
        <p className="mt-3 text-slate-600">Структура готова для створення замовлення. Підключення відправки замовлення буде наступним кроком.</p>
        <form className="mt-6 space-y-4">
          <input name="name" placeholder="Імʼя та прізвище" className="w-full rounded border p-3" />
          <input name="email" type="email" placeholder="Email" className="w-full rounded border p-3" />
          <input name="phone" placeholder="Телефон" className="w-full rounded border p-3" />
          <button type="button" className="w-full rounded bg-slate-300 p-3 text-slate-700">
            Створення замовлення буде додано окремо
          </button>
        </form>
      </section>
      <aside className="rounded-2xl bg-white p-6 shadow">
        <h2 className="text-xl font-bold">Ваше замовлення</h2>
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <div key={item.productId} className="flex justify-between gap-4">
              <span>{item.name} × {item.quantity}</span>
              <span>{formatPrice(item.unitPrice * item.quantity)}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 border-t pt-4 text-lg font-bold">Разом: {formatPrice(cartTotal(items))}</div>
      </aside>
    </div>
  );
}
