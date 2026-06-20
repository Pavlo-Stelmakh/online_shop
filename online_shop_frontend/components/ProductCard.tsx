"use client";

import type { Product } from "@/types";
import { addProductToCart, formatPrice } from "@/lib/cart";
import { isProductValidForCart } from "@/lib/products";

export default function ProductCard({ product }: { product: Product }) {
  const canAdd = isProductValidForCart(product);

  return (
    <article className="flex flex-col overflow-hidden rounded-2xl border bg-white shadow-sm">
      <div className="flex h-48 items-center justify-center bg-slate-100">
        {product.imageUrl ? (
          <img src={product.imageUrl} alt={product.name} className="h-full w-full object-cover" />
        ) : (
          <span className="text-slate-500">Немає фото</span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <h2 className="text-lg font-semibold">{product.name}</h2>
        <p className="text-sm text-slate-600">{product.description || "Опис відсутній"}</p>
        <p className="text-xl font-bold text-blue-700">{formatPrice(product.price, product.priceAmount)}</p>
        <p className="text-sm text-slate-600">На складі: {Number.isFinite(product.stock) ? product.stock : 0}</p>
        <button
          type="button"
          disabled={!canAdd}
          onClick={() => addProductToCart(product)}
          className="mt-auto rounded bg-blue-600 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Додати в кошик
        </button>
      </div>
    </article>
  );
}
