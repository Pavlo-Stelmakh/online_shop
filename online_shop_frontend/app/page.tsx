import ProductCard from "@/components/ProductCard";
import { getProducts } from "@/lib/api";

export default async function HomePage() {
  const products = await getProducts();

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Каталог товарів</h1>
          <p className="mt-2 text-gray-600">
            Новий frontend підключений до FastAPI backend.
          </p>
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