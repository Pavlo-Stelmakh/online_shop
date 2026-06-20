"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getAccessToken } from "@/lib/auth";
import { clearCart, getCart } from "@/lib/cart";
import { createOrderFromCart } from "@/lib/orders";
import type { CartItem } from "@/types";

export default function CheckoutPage() {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdOrderId, setCreatedOrderId] = useState<number | null>(null);

  useEffect(() => {
    setCart(getCart());
    setAccessToken(getAccessToken());
  }, []);

  const total = useMemo(() => cart.reduce((sum, item) => sum + item.price * item.quantity, 0), [cart]);

  async function handleCreateOrder() {
    if (!accessToken || cart.length === 0) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const order = await createOrderFromCart(cart, accessToken);
      clearCart();
      setCart([]);
      setCreatedOrderId(order.id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не вдалося створити замовлення.";
      setError(`${message} Перевірте товари в кошику або спробуйте пізніше.`);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (createdOrderId !== null) {
    return (
      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h1 className="text-3xl font-bold text-slate-950">Замовлення створено</h1>
        <p className="mt-4 text-slate-700">Дякуємо! Ваше замовлення №{createdOrderId} успішно створено.</p>
        <Link className="mt-6 inline-block rounded-xl bg-slate-950 px-4 py-2 font-semibold text-white hover:bg-slate-800" href="/">
          Повернутися до каталогу
        </Link>
      </section>
    );
  }

  if (cart.length === 0) {
    return <p className="rounded-2xl bg-white p-6 text-slate-600">Кошик порожній. Додайте товари перед оформленням.</p>;
  }

  if (!accessToken) {
    return (
      <section className="rounded-2xl bg-white p-6 text-slate-600">
        <p>Увійдіть, щоб оформити замовлення.</p>
        <Link className="mt-4 inline-block rounded-xl bg-slate-950 px-4 py-2 font-semibold text-white hover:bg-slate-800" href="/login">
          Увійти
        </Link>
      </section>
    );
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
        {error && <p className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <button
          className="mt-6 w-full rounded-xl bg-slate-950 px-4 py-2 font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          onClick={handleCreateOrder}
          type="button"
        >
          {isSubmitting ? "Створення..." : "Створити замовлення"}
        </button>
        <p className="mt-3 text-sm text-slate-600">Оплата та доставка будуть узгоджені окремо. Онлайн-оплата ще не реалізована.</p>
      </div>
    </section>
  );
}
