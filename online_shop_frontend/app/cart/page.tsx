"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { CartItem } from "@/types";
import { cartTotal, formatPrice, getCart, saveCart } from "@/lib/cart";

export default function CartPage() {
  const [items, setItems] = useState<CartItem[]>([]);

  useEffect(() => {
    setItems(getCart());
  }, []);

  function update(nextItems: CartItem[]) {
    saveCart(nextItems);
    setItems(nextItems);
  }

  function changeQuantity(productId: number, quantity: number) {
    update(items.map((item) => (item.productId === productId ? { ...item, quantity: Math.min(Math.max(quantity, 1), item.stock) } : item)));
  }

  if (!items.length) {
    return (
      <div className="rounded-xl bg-white p-8 text-center">
        <h1 className="text-2xl font-bold">Кошик порожній</h1>
        <Link className="mt-4 inline-block rounded bg-blue-600 px-4 py-2 text-white" href="/">
          До каталогу
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">Кошик</h1>
      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.productId} className="grid gap-4 rounded-xl bg-white p-4 shadow-sm md:grid-cols-[1fr_auto_auto_auto] md:items-center">
            <div>
              <h2 className="font-semibold">{item.name}</h2>
              <p className="text-sm text-slate-600">Кількість на складі: {item.stock}</p>
              <p className="text-sm text-slate-600">Ціна за одиницю: {formatPrice(item.unitPrice, item.priceAmount)}</p>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" className="rounded border px-3 py-1" onClick={() => changeQuantity(item.productId, item.quantity - 1)}>
                −
              </button>
              <span className="min-w-8 text-center">{item.quantity}</span>
              <button type="button" className="rounded border px-3 py-1 disabled:text-slate-300" disabled={item.quantity >= item.stock} onClick={() => changeQuantity(item.productId, item.quantity + 1)}>
                +
              </button>
            </div>
            <div className="font-semibold">{formatPrice(item.unitPrice * item.quantity)}</div>
            <button type="button" className="text-left text-red-600 md:text-center" onClick={() => update(items.filter((x) => x.productId !== item.productId))}>
              Видалити
            </button>
          </div>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl bg-white p-4 shadow-sm">
        <strong>Разом: {formatPrice(cartTotal(items))}</strong>
        <div className="flex gap-3">
          <button type="button" className="rounded border px-4 py-2" onClick={() => update([])}>
            Очистити кошик
          </button>
          <Link className="rounded bg-blue-600 px-4 py-2 text-white" href="/checkout">
            Оформити замовлення
          </Link>
        </div>
      </div>
    </div>
  );
}
