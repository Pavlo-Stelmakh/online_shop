import Image from "next/image";

import { getProducts } from "../lib/products";

export const dynamic = "force-dynamic";

export default async function Home() {
  const products = await getProducts();

  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Клієнтська панель online shop
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Каталог</h1>
        <p className="max-w-2xl text-base text-slate-600">
          Переглядайте товари з актуального каталогу магазину.
        </p>
      </div>

      {products.length > 0 ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => (
            <article
              key={product.id}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              <div className="relative flex h-48 items-center justify-center bg-slate-100">
                {product.image_url ? (
                  <Image
                    src={product.image_url}
                    alt={product.name}
                    fill
                    className="object-cover"
                    sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                    unoptimized
                  />
                ) : (
                  <span className="text-sm font-medium text-slate-500">Немає фото</span>
                )}
              </div>

              <div className="space-y-4 p-5">
                <div className="space-y-2">
                  <h2 className="text-xl font-semibold text-slate-950">{product.name}</h2>
                  <p className="line-clamp-3 text-sm text-slate-600">{product.description}</p>
                </div>

                <div className="flex items-center justify-between gap-4">
                  <p className="text-lg font-bold text-slate-950">{product.price_amount} грн</p>
                  <p className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    В наявності: {product.stock}
                  </p>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
          <p className="text-lg text-slate-700">Каталог товарів наразі порожній.</p>
        </div>
      )}
    </section>
  );
}
