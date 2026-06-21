import Image from "next/image";
import { getProducts } from "../lib/products";

export const dynamic = "force-dynamic";

export default async function Home() {
  try {
    const products = await getProducts();

    return (
      <section className="space-y-8">
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Клієнтська панель online shop
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Каталог</h1>
        </div>

        {products.length > 0 ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {products.map((product) => (
              <article
                key={product.id}
                className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
              >
                <div className="relative flex aspect-[4/3] items-center justify-center bg-slate-100">
                  {product.image_url ? (
                    <Image
                      src={product.image_url}
                      alt={product.name}
                      fill
                      sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                      className="object-cover"
                      unoptimized
                    />
                  ) : (
                    <span className="text-sm font-medium text-slate-500">Немає фото</span>
                  )}
                </div>
                <div className="space-y-3 p-5">
                  <div className="space-y-1">
                    <h2 className="text-xl font-semibold text-slate-950">{product.name}</h2>
                    <p className="line-clamp-3 text-sm leading-6 text-slate-600">{product.description}</p>
                  </div>
                  <p className="text-lg font-bold text-slate-950">
                    {product.price_amount ?? product.price.toFixed(2)} грн
                  </p>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
            <p className="text-lg text-slate-700">У каталозі поки немає товарів.</p>
          </div>
        )}
      </section>
    );
  } catch (error) {
    console.error(error);

    return (
      <section className="space-y-8">
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Клієнтська панель online shop
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Каталог</h1>
        </div>

        <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center shadow-sm sm:p-12">
          <p className="text-lg font-medium text-red-800">Не вдалося завантажити каталог товарів.</p>
        </div>
      </section>
    );
  }
}
