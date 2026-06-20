"use client";

import { useState } from "react";
import { addToCart } from "@/lib/cart";
import type { Product } from "@/types";

type ProductCardProps = {
  product: Product;
};

export function ProductCard({ product }: ProductCardProps) {
  const [added, setAdded] = useState(false);
  const canAdd = Number(product.id) > 0 && Number(product.stock) > 0;

  function handleAddToCart() {
    if (!canAdd) {
      return;
    }

    addToCart(product);
    setAdded(true);
    window.setTimeout(() => setAdded(false), 1200);
  }

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex h-48 items-center justify-center bg-slate-100 text-slate-500">
        {product.imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={product.name} className="h-full w-full object-cover" src={product.imageUrl} />
        ) : (
          <span>Немає фото</span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-5">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">{product.name}</h2>
          <p className="mt-1 min-h-12 text-sm text-slate-600">{product.description || "Опис відсутній"}</p>
        </div>
        <div className="mt-auto space-y-2">
          <p className="text-xl font-bold text-slate-950">{product.price.toFixed(2)} грн</p>
          <p className="text-sm text-slate-600">В наявності: {product.stock}</p>
          <button
            className={`w-full rounded-xl px-4 py-2 font-semibold transition ${
              canAdd
                ? "cursor-pointer bg-slate-950 text-white hover:bg-slate-800"
                : "cursor-not-allowed bg-slate-200 text-slate-500"
            }`}
            disabled={!canAdd}
            onClick={handleAddToCart}
            type="button"
          >
            {added ? "Додано" : "Додати в кошик"}
          </button>
        </div>
      </div>
    </article>
  );
}
