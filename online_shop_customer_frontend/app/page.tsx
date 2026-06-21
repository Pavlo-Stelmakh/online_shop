import { ProductCard } from "./ProductCard";
import { getProducts, type Product } from "../lib/products";

export const dynamic = "force-dynamic";

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
