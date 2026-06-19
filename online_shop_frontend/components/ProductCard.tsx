"use client";

import Link from "next/link";
import type { Product } from "@/types";
import { addProductToCart, formatPrice } from "@/lib/cart";

export default function ProductCard({ product }: { product: Product }) {
  return <article className="flex flex-col overflow-hidden rounded-2xl border bg-white shadow-sm"><div className="flex h-48 items-center justify-center bg-slate-100">{product.image_url ? <img src={product.image_url} alt={product.name} className="h-full w-full object-cover" /> : <span className="text-slate-500">Немає фото</span>}</div><div className="flex flex-1 flex-col gap-3 p-4"><h2 className="text-lg font-semibold">{product.name}</h2><p className="text-xl font-bold text-blue-700">{formatPrice(product.price, product.price_amount)}</p><p className="text-sm text-slate-600">На складі: {product.stock}</p><div className="mt-auto flex gap-2"><Link className="flex-1 rounded border px-3 py-2 text-center" href={`/products/${product.id}`}>Деталі</Link><button disabled={product.stock < 1} onClick={() => addProductToCart(product)} className="flex-1 rounded bg-blue-600 px-3 py-2 text-white disabled:bg-slate-300">Додати в кошик</button></div></div></article>;
}
