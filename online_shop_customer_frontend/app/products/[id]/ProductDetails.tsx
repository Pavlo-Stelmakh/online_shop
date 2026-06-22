"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { addToCart } from "../../../lib/cart";
import type { Product } from "../../../lib/products";

function isValidImageUrl(imageUrl: string) {
  return imageUrl.startsWith("http://") || imageUrl.startsWith("https://");
}

function formatPrice(product: Product) {
  const price = product.price_amount ? Number(product.price_amount) : product.price;

  return `${price.toFixed(2)} грн`;
}

export function ProductDetails({ product }: { product: Product }) {
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const imageUrl = product.image_url?.trim() ?? "";
  const hasImage = Boolean(imageUrl) && isValidImageUrl(imageUrl) && !imageLoadFailed;
  const isInStock = product.stock > 0;

  useEffect(() => {
    setImageLoadFailed(false);
  }, [imageUrl]);

  function handleAddToCart() {
    addToCart(product);
  }

  return (
    <article className="grid gap-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:p-8">
      <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-2xl bg-slate-100">
        {hasImage ? (
          <Image
            src={imageUrl}
            alt={product.name}
            fill
            sizes="(min-width: 1024px) 50vw, 100vw"
            className="object-cover"
            onError={() => setImageLoadFailed(true)}
          />
        ) : (
          <span className="flex h-full w-full items-center justify-center text-center text-sm font-medium text-slate-500">
            Немає фото
          </span>
        )}
      </div>

      <div className="flex flex-col justify-center space-y-6">
        <div className="space-y-3">
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">{product.name}</h1>
          <p className="text-base leading-7 text-slate-600">{product.description}</p>
        </div>

        <div>
          <p className="text-2xl font-bold text-slate-950">{formatPrice(product)}</p>
          <p className="text-sm text-slate-600">В наявності: {product.stock}</p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={handleAddToCart}
            disabled={!isInStock}
            className="rounded-full bg-slate-950 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          >
            {isInStock ? "Додати в кошик" : "Немає в наявності"}
          </button>
          <Link
            href="/"
            className="rounded-full border border-slate-300 px-5 py-2 text-center text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Повернутися до каталогу
          </Link>
        </div>
      </div>
    </article>
  );
}
