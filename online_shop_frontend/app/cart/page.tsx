"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { CartItem } from "@/types";
import { cartTotal, formatPrice, getCart, saveCart } from "@/lib/cart";

export default function CartPage() {
  const [items, setItems] = useState<CartItem[]>([]);
  const refresh = () => setItems(getCart());
  useEffect(() => { refresh(); window.addEventListener("cart-changed", refresh); return () => window.removeEventListener("cart-changed", refresh); }, []);
  const update = (next: CartItem[]) => { saveCart(next); setItems(next); };
  if (!items.length) return <div className="rounded-xl bg-white p-8 text-center"><h1 className="text-2xl font-bold">Кошик порожній</h1><Link className="mt-4 inline-block rounded bg-blue-600 px-4 py-2 text-white" href="/">До каталогу</Link></div>;
  return <div><h1 className="mb-6 text-3xl font-bold">Кошик</h1><div className="space-y-4">{items.map((item) => <div key={item.productId} className="grid gap-4 rounded-xl bg-white p-4 md:grid-cols-[1fr_auto_auto_auto]"><div><h2 className="font-semibold">{item.name}</h2><p className="text-sm text-slate-600">Ціна: {formatPrice(item.unitPrice, item.priceAmount)}</p></div><div className="flex items-center gap-2"><button className="rounded border px-3 py-1" onClick={() => update(items.map((x) => x.productId === item.productId ? { ...x, quantity: Math.max(1, x.quantity - 1) } : x))}>−</button><span>{item.quantity}</span><button className="rounded border px-3 py-1" onClick={() => update(items.map((x) => x.productId === item.productId ? { ...x, quantity: Math.min((x.stock ?? x.quantity + 1), x.quantity + 1) } : x))}>+</button></div><div className="font-semibold">{formatPrice(item.unitPrice * item.quantity)}</div><button className="text-red-600" onClick={() => update(items.filter((x) => x.productId !== item.productId))}>Видалити</button></div>)}</div><div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl bg-white p-4"><strong>Разом: {formatPrice(cartTotal(items))}</strong><div className="flex gap-3"><button className="rounded border px-4 py-2" onClick={() => update([])}>Очистити кошик</button><Link className="rounded bg-blue-600 px-4 py-2 text-white" href="/checkout">Оформити замовлення</Link></div></div></div>;
}
