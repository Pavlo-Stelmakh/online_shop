import { getProducts, type Product } from "../lib/products";

function formatPrice(price: Product["price"]) {
  const numericPrice = Number(price ?? 0);

  if (!Number.isFinite(numericPrice)) {
    return "Ціну уточнюйте";
  }

  return `${new Intl.NumberFormat("uk-UA", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(numericPrice)} грн`;
}

function ProductCard({ product }: { product: Product }) {
  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {product.image_url ? (
        <img
          src={product.image_url}
          alt={product.name || "Фото товару"}
          className="h-56 w-full object-cover"
        />
      ) : (
        <div className="flex h-56 w-full items-center justify-center bg-slate-100 text-sm font-medium text-slate-500">
          Немає фото
        </div>
      )}

      <div className="space-y-3 p-5">
        <div className="space-y-2">
          <h2 className="text-xl font-semibold text-slate-950">{product.name || "Товар без назви"}</h2>
          <p className="line-clamp-3 text-sm leading-6 text-slate-600">
            {product.description || "Опис товару поки що відсутній."}
          </p>
        </div>

        <div className="flex flex-col gap-1 border-t border-slate-100 pt-4">
          <p className="text-lg font-bold text-slate-950">{formatPrice(product.price)}</p>
          <p className="text-sm text-slate-600">В наявності: {product.stock ?? 0}</p>
        </div>
      </div>
    </article>
  );
}

export default async function Home() {
  let products: Product[] = [];
  let errorMessage = "";

  try {
    products = await getProducts();
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : "Сталася невідома помилка.";
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
          <p className="text-lg font-semibold text-red-900">Не вдалося завантажити каталог.</p>
          <p className="mt-2 text-sm text-red-700">{errorMessage}</p>
          <p className="mt-4 text-sm text-red-700">Спробуйте оновити сторінку трохи пізніше.</p>
        </div>
      ) : products.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
          <p className="text-lg text-slate-700">У каталозі поки що немає товарів.</p>
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product, index) => (
            <ProductCard key={product.id ?? `${product.name ?? "product"}-${index}`} product={product} />
          ))}
        </div>
      )}
    </section>
  );
}
