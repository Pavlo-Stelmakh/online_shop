"use client";

import { useEffect, useMemo, useState } from "react";
import { clearCart, getCart, saveCart } from "@/lib/cart";
import type { CartItem } from "@/types";

export default function CartPage() {
  const [cart, setCart] = useState<CartItem[]>([]);

  useEffect(() => {
    setCart(getCart());
  }, []);

  const total = useMemo(() => cart.reduce((sum, item) => sum + item.price * item.quantity, 0), [cart]);

  function updateQuantity(id: number, quantity: number) {
    const nextCart = cart.map((item) =>
      item.id === id ? { ...item, quantity: Math.max(1, Math.min(quantity, item.stock)) } : item,
    );
    setCart(nextCart);
    saveCart(nextCart);
  }

  function removeItem(id: number) {
    const nextCart = cart.filter((item) => item.id !== id);
    setCart(nextCart);
    saveCart(nextCart);
  }

  function handleClearCart() {
    clearCart();
    setCart([]);
  }

  if (cart.length === 0) {
    return <p className="rounded-2xl bg-white p-6 text-slate-600">Кошик порожній</p>;
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-3xl font-bold text-slate-950">Кошик</h1>
        <button className="rounded-xl border border-slate-300 px-4 py-2 font-semibold hover:bg-slate-100" onClick={handleClearCart} type="button">
          Очистити кошик
        </button>
      </div>

      <div className="space-y-4">
        {cart.map((item) => (
          <article className="rounded-2xl border border-slate-200 bg-white p-5" key={item.id}>
            <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">{item.name}</h2>
                <p className="text-sm text-slate-600">Ціна: {item.price.toFixed(2)} грн</p>
                <p className="text-sm text-slate-600">Разом: {(item.price * item.quantity).toFixed(2)} грн</p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button className="rounded-lg border px-3 py-1 disabled:cursor-not-allowed disabled:opacity-50" disabled={item.quantity <= 1} onClick={() => updateQuantity(item.id, item.quantity - 1)} type="button">
                  −
                </button>
                <span className="min-w-8 text-center font-semibold">{item.quantity}</span>
                <button className="rounded-lg border px-3 py-1 disabled:cursor-not-allowed disabled:opacity-50" disabled={item.quantity >= item.stock} onClick={() => updateQuantity(item.id, item.quantity + 1)} type="button">
                  +
                </button>
                <button className="rounded-lg bg-red-600 px-3 py-1 text-white hover:bg-red-700" onClick={() => removeItem(item.id)} type="button">
                  Видалити
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="rounded-2xl bg-slate-950 p-6 text-right text-xl font-bold text-white">Загальна сума: {total.toFixed(2)} грн</div>
    </section>
  );
}
