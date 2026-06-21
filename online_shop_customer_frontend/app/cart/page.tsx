"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  clearCart,
  getCart,
  removeFromCart,
  updateCartItemQuantity,
  type CartItem,
} from "../../lib/cart";

function getDisplayPrice(item: CartItem) {
  const priceAmount = item.price_amount ? Number(item.price_amount) : item.price;

  return Number.isFinite(priceAmount) ? priceAmount : item.price;
}

function formatPrice(price: number) {
  return `${price.toFixed(2)} грн`;
}

export default function CartPage() {
  const [cartItems, setCartItems] = useState<CartItem[]>([]);

  useEffect(() => {
    setCartItems(getCart());
  }, []);

  const cartTotal = cartItems.reduce((total, item) => total + getDisplayPrice(item) * item.quantity, 0);

  function handleUpdateQuantity(productId: number, quantity: number) {
    setCartItems(updateCartItemQuantity(productId, quantity));
  }

  function handleRemove(productId: number) {
    setCartItems(removeFromCart(productId));
  }

  function handleClearCart() {
    clearCart();
    setCartItems([]);
  }

  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Клієнтська панель online shop</p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Кошик</h1>
      </div>

      {cartItems.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
          <p className="text-lg text-slate-700">Кошик порожній.</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="divide-y divide-slate-200 rounded-2xl border border-slate-200 bg-white shadow-sm">
            {cartItems.map((item) => {
              const price = getDisplayPrice(item);
              const canDecrease = item.quantity > 1;
              const canIncrease = item.quantity < item.stock;

              return (
                <article key={item.id} className="grid gap-4 p-5 sm:grid-cols-[1fr_auto] sm:items-center">
                  <div className="space-y-2">
                    <h2 className="text-xl font-semibold text-slate-950">{item.name}</h2>
                    <p className="text-sm text-slate-600">Ціна: {formatPrice(price)}</p>
                    <p className="text-sm text-slate-600">Кількість: {item.quantity}</p>
                    <p className="font-semibold text-slate-950">Разом: {formatPrice(price * item.quantity)}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                    <button
                      type="button"
                      onClick={() => handleUpdateQuantity(item.id, item.quantity - 1)}
                      disabled={!canDecrease}
                      className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      -
                    </button>
                    <button
                      type="button"
                      onClick={() => handleUpdateQuantity(item.id, item.quantity + 1)}
                      disabled={!canIncrease}
                      className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      +
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemove(item.id)}
                      className="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
                    >
                      Видалити
                    </button>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xl font-bold text-slate-950">Загальна сума: {formatPrice(cartTotal)}</p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
              <Link
                href="/checkout"
                className="rounded-full bg-emerald-600 px-5 py-2 text-center text-sm font-semibold text-white transition hover:bg-emerald-700"
              >
                Оформити замовлення
              </Link>
              <button
                type="button"
                onClick={handleClearCart}
                className="rounded-full bg-slate-950 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                Очистити кошик
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
