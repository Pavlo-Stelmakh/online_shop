import Image from "next/image";

import { getProducts, type Product } from "../lib/products";

export const dynamic = "force-dynamic";

function isValidImageUrl(imageUrl?: string | null) {
  return Boolean(imageUrl && (imageUrl.startsWith("http://") || imageUrl.startsWith("https://")));
}

function formatPrice(product: Product) {
  const price = product.price_amount ? Number(product.price_amount) : product.price;

  return `${price.toFixed(2)} грн`;
}

function ProductCard({ product }: { product: Product }) {
  const hasImage = isValidImageUrl(product.image_url);

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

      <div className="space-y-3 p-5">
        <div className="space-y-2">
          <h2 className="text-xl font-semibold text-slate-950">{product.name}</h2>
          <p className="text-sm leading-6 text-slate-600">{product.description}</p>
        </div>

        <div>
          <p className="text-lg font-bold text-slate-950">{formatPrice(product)}</p>
          <p className="text-sm text-slate-600">В наявності: {product.stock}</p>
        </div>
      </div>
    </article>
  );
}

export default async function Home() {
  let products: Product[] = [];
  let errorMessage: string | null = null;

  try {
    products = await getProducts();
  } catch (error) {
    console.error(error);
    errorMessage = "Не вдалося завантажити каталог товарів.";
  }

  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Клієнтська панель online shop
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Каталог</h1>
      </div>

      {errorMessage ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center shadow-sm sm:p-12">
          <p className="text-lg font-medium text-red-700">{errorMessage}</p>
        </div>
      ) : products.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
          <p className="text-lg text-slate-700">Каталог товарів порожній.</p>
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </section>
  );
}
