"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { cartTotal, formatPrice, getCart, saveCart } from "@/lib/cart";
import { getAccessToken } from "@/lib/auth";
import type { CartItem } from "@/types";

export default function CheckoutPage() {
  const router = useRouter(); const [items, setItems] = useState<CartItem[]>([]); const [token, setToken] = useState<string | null>(null); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { setItems(getCart()); const accessToken = getAccessToken(); setToken(accessToken); if (!accessToken) router.replace("/login?next=/checkout"); }, [router]);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!token || !items.length) return; setLoading(true); setError(""); const data = new FormData(event.currentTarget); const profile = { name: String(data.get("name")), email: String(data.get("email")), phone: String(data.get("phone")) }; try { let customer; try { customer = await api.getMyCustomer(token); } catch (e) { if (e instanceof ApiError && e.status === 404) customer = await api.createCustomer(token, profile); else throw e; } await api.createOrder(token, customer.id, items.map((item) => ({ product_id: item.productId, quantity: item.quantity }))); saveCart([]); router.push("/order-success"); } catch (e) { setError(e instanceof Error ? e.message : "Не вдалося створити замовлення"); } finally { setLoading(false); } }
  if (!token) return <div className="rounded-xl bg-white p-8 text-center">Переходимо на сторінку входу...</div>;
  if (!items.length) return <div className="rounded-xl bg-white p-8 text-center"><h1 className="text-2xl font-bold">Кошик порожній</h1><p className="mt-2 text-slate-600">Додайте товари перед оформленням.</p><Link className="mt-4 inline-block rounded bg-blue-600 px-4 py-2 text-white" href="/">До каталогу</Link></div>;
  return <div className="grid gap-8 md:grid-cols-2"><section className="rounded-2xl bg-white p-6 shadow"><h1 className="text-2xl font-bold">Оформлення замовлення</h1>{error && <p className="mt-4 rounded bg-red-50 p-3 text-red-700">{error}</p>}<form onSubmit={submit} className="mt-6 space-y-4"><input required name="name" placeholder="Імʼя та прізвище" className="w-full rounded border p-3" /><input required name="email" type="email" placeholder="Email" className="w-full rounded border p-3" /><input required name="phone" placeholder="Телефон" className="w-full rounded border p-3" /><button disabled={loading || !items.length} className="w-full rounded bg-blue-600 p-3 text-white disabled:bg-slate-300">{loading ? "Створюємо замовлення..." : "Підтвердити замовлення"}</button></form></section><aside className="rounded-2xl bg-white p-6 shadow"><h2 className="text-xl font-bold">Ваше замовлення</h2><div className="mt-4 space-y-3">{items.map((item) => <div key={item.productId} className="flex justify-between gap-4"><span>{item.name} × {item.quantity}</span><span>{formatPrice(item.unitPrice * item.quantity)}</span></div>)}</div><div className="mt-4 border-t pt-4 text-lg font-bold">Разом: {formatPrice(cartTotal(items))}</div></aside></div>;
}
