"use client";


import Link from "next/link";
import { useState } from "react";
import Header from "@/components/Header";

import {
  clearCart,
  getCartItems,
  getCartTotal,
  removeFromCart,
  updateCartItemQuantity,
  type CartItem,
} from "@/lib/cart";

export default function CartPage() {
  const [items, setItems] = useState<CartItem[]>(() => getCartItems());

  const total = getCartTotal(items);

  function handleDecrease(productId: number, currentQuantity: number) {
    setItems(updateCartItemQuantity(productId, currentQuantity - 1));
  }

  function handleIncrease(productId: number, currentQuantity: number) {
    setItems(updateCartItemQuantity(productId, currentQuantity + 1));
  }

  function handleRemove(productId: number) {
    setItems(removeFromCart(productId));
  }

  function handleClearCart() {
    clearCart();
    setItems([]);
  }

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">

        <Header
          title="Кошик"
          description="Товари, які ви додали до замовлення."
        />
        
        {items.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <p className="text-gray-700">Кошик порожній.</p>
            <Link href="/" className="mt-4 inline-block rounded-lg bg-black px-4 py-2 text-white">
              Перейти до каталогу
            </Link>
          </div>
        ) : (
          <section className="space-y-4">
            {items.map((item) => (
              <article
                key={item.product.id}
                className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-gray-500">{item.product.categoryName}</p>
                    <h2 className="text-xl font-semibold text-gray-900">{item.product.name}</h2>
                    <p className="mt-1 text-gray-600">
                      {item.product.price.toFixed(2)} грн за одиницю
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => handleDecrease(item.product.id, item.quantity)}
                      className="h-9 w-9 rounded-lg border border-gray-300 text-lg"
                    >
                      -
                    </button>

                    <span className="min-w-8 text-center text-lg font-semibold">
                      {item.quantity}
                    </span>

                    <button
                      type="button"
                      onClick={() => handleIncrease(item.product.id, item.quantity)}
                      className="h-9 w-9 rounded-lg border border-gray-300 text-lg"
                    >
                      +
                    </button>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4">
                  <p className="font-semibold text-gray-900">
                    Разом: {(item.product.price * item.quantity).toFixed(2)} грн
                  </p>

                  <button
                    type="button"
                    onClick={() => handleRemove(item.product.id)}
                    className="text-sm font-medium text-red-700"
                  >
                    Видалити
                  </button>
                </div>
              </article>
            ))}

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-xl font-bold text-gray-900">Всього</p>
                <p className="text-xl font-bold text-gray-900">{total.toFixed(2)} грн</p>
              </div>

              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  className="rounded-lg bg-black px-4 py-2 text-white"
                >
                  Оформити замовлення
                </button>

                <button
                  type="button"
                  onClick={handleClearCart}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-gray-800"
                >
                  Очистити кошик
                </button>
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}