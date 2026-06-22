import Link from "next/link";
import ProductCard from "@/components/ProductCard";
import { getProducts } from "@/lib/api";

export default async function HomePage() {
  const products = await getProducts();

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-6xl">

        <header className="mb-8 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Каталог товарів</h1>
            <p className="mt-2 text-gray-600">
              Новий frontend підключений до FastAPI backend.
            </p>
          </div>

          <Link href="/cart" className="rounded-lg bg-black px-4 py-2 text-white">
            Кошик
          </Link>
        </header>









        {products.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-gray-600">
            Товари поки не знайдені.
          </div>
        ) : (
          <section className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </section>
        )}
      </div>
    </main>
  );
}