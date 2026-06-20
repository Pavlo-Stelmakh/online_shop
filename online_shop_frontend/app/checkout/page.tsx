"use client";

import { useEffect, useMemo, useState } from "react";
import { getAccessToken } from "@/lib/auth";
import { getCart } from "@/lib/cart";
import type { CartItem } from "@/types";

export default function CheckoutPage() {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setCart(getCart());
    setHasToken(Boolean(getAccessToken()));
  }, []);

  const total = useMemo(() => cart.reduce((sum, item) => sum + item.price * item.quantity, 0), [cart]);

  if (cart.length === 0) {
    return <p className="rounded-2xl bg-white p-6 text-slate-600">Кошик порожній. Додайте товари перед оформленням.</p>;
  }

  if (!hasToken) {
    return <p className="rounded-2xl bg-white p-6 text-slate-600">Увійдіть, щоб перейти до оформлення замовлення.</p>;
  }

  return (
    <section className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-950">Оформлення замовлення</h1>
      <div className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-950">Підсумок замовлення</h2>
        <ul className="mt-4 divide-y divide-slate-200">
          {cart.map((item) => (
            <li className="flex justify-between gap-4 py-3" key={item.id}>
              <span>{item.name} × {item.quantity}</span>
              <span className="font-semibold">{(item.price * item.quantity).toFixed(2)} грн</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-right text-xl font-bold">Разом: {total.toFixed(2)} грн</p>
        <p className="mt-3 text-sm text-slate-600">Створення замовлення на бекенді буде додано пізніше.</p>
      </div>
    </section>
  );
}
