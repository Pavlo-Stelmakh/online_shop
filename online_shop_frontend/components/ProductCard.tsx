"use client";

import { useState } from "react";
import type { Product } from "@/types";
import { addToCart } from "@/lib/cart";

type ProductCardProps = {
  product: Product;
};

export default function ProductCard({ product }: ProductCardProps) {
  const [added, setAdded] = useState(false);
  const isAvailable = product.stock > 0;

  function handleAddToCart() {
    addToCart(product);
    setAdded(true);

    window.setTimeout(() => {
      setAdded(false);
    }, 1500);
  }

  return (
    <article className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3">
        <p className="text-sm text-gray-500">{product.categoryName}</p>
        <h2 className="text-xl font-semibold text-gray-900">{product.name}</h2>
      </div>

      {product.description && (
        <p className="mb-4 text-sm text-gray-600">{product.description}</p>
      )}

      <div className="mb-4 flex items-center justify-between">
        <p className="text-lg font-bold text-gray-900">
          {product.price.toFixed(2)} грн
        </p>

        <p className={isAvailable ? "text-sm text-green-700" : "text-sm text-red-700"}>
          {isAvailable ? `В наявності: ${product.stock}` : "Немає в наявності"}
        </p>
      </div>

      <button
        type="button"
        disabled={!isAvailable}
        onClick={handleAddToCart}
        className="w-full rounded-lg bg-black px-4 py-2 text-white disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        {added ? "Додано" : "Додати в кошик"}
      </button>
    </article>
  );
}