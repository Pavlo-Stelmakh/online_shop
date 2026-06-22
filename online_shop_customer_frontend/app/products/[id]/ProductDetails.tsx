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
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const imageUrl = product.image_url?.trim() ?? "";
  const hasImageUrl = Boolean(imageUrl) && isValidImageUrl(imageUrl);
  const shouldShowImage = hasImageUrl && !imageLoadFailed;
  const isInStock = product.stock > 0;

  useEffect(() => {
    setImageLoadFailed(false);
  }, [imageUrl]);

  function handleAddToCart() {
    addToCart(product);
    setShowSuccessMessage(true);
    window.setTimeout(() => setShowSuccessMessage(false), 2500);
  }

  return (
    <section className="space-y-8">
      <Link href="/" className="inline-flex text-sm font-semibold text-slate-700 transition hover:text-slate-950">
        Повернутися до каталогу
      </Link>

      <article className="grid gap-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2 md:p-8">
        <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-2xl bg-slate-100">
          {shouldShowImage ? (
            <Image
              src={imageUrl}
              alt={product.name}
              fill
              sizes="(min-width: 768px) 50vw, 100vw"
              className="object-cover"
              onError={() => setImageLoadFailed(true)}
              priority
            />
          ) : (
            <span className="text-sm font-medium text-slate-500">Немає фото</span>
          )}
        </div>

        <div className="flex flex-col justify-center space-y-6">
          <div className="space-y-3">
            <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">{product.name}</h1>
            <p className="text-base leading-7 text-slate-600">{product.description}</p>
          </div>

          <div className="space-y-1">
            <p className="text-2xl font-bold text-slate-950">{formatPrice(product)}</p>
            <p className="text-sm text-slate-600">В наявності: {product.stock}</p>
          </div>

          <div className="space-y-2">
            <button
              type="button"
              onClick={handleAddToCart}
              disabled={!isInStock}
              className="w-full rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600 sm:w-auto"
            >
              {isInStock ? "Додати в кошик" : "Немає в наявності"}
            </button>
            {showSuccessMessage ? <p className="text-sm font-medium text-green-700">Товар додано в кошик.</p> : null}
          </div>
        </div>
      </article>
    </section>
  );
}
