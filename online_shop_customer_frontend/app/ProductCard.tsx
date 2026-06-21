"use client";

import Image from "next/image";
import { useState } from "react";

import { addToCart } from "../lib/cart";
import type { Product } from "../lib/products";

function isValidImageUrl(imageUrl?: string | null) {
  return Boolean(imageUrl && (imageUrl.startsWith("http://") || imageUrl.startsWith("https://")));
}

function formatPrice(product: Product) {
  const price = product.price_amount ? Number(product.price_amount) : product.price;

  return `${price.toFixed(2)} грн`;
}

export function ProductCard({ product }: { product: Product }) {
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);
  const hasImage = isValidImageUrl(product.image_url);
  const isInStock = product.stock > 0;

  function handleAddToCart() {
    addToCart(product);
    setShowSuccessMessage(true);
    window.setTimeout(() => setShowSuccessMessage(false), 2500);
  }

  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="relative flex aspect-[4/3] items-center justify-center bg-slate-100">
        {hasImage ? (
          <Image
            src={product.image_url as string}
            alt={product.name}
            fill
            sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
            className="object-cover"
          />
        ) : (
          <span className="text-sm font-medium text-slate-500">Немає фото</span>
        )}
      </div>

      <div className="space-y-4 p-5">
        <div className="space-y-2">
          <h2 className="text-xl font-semibold text-slate-950">{product.name}</h2>
          <p className="text-sm leading-6 text-slate-600">{product.description}</p>
        </div>

        <div>
          <p className="text-lg font-bold text-slate-950">{formatPrice(product)}</p>
          <p className="text-sm text-slate-600">В наявності: {product.stock}</p>
        </div>

        <div className="space-y-2">
          <button
            type="button"
            onClick={handleAddToCart}
            disabled={!isInStock}
            className="w-full rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          >
            {isInStock ? "Додати в кошик" : "Немає в наявності"}
          </button>
          {showSuccessMessage ? <p className="text-sm font-medium text-green-700">Товар додано в кошик.</p> : null}
        </div>
      </div>
    </article>
  );
}
