import Header from "@/components/Header";
import ProductCard from "@/components/ProductCard";
import { getProducts } from "@/lib/api";

export default async function HomePage() {
  const products = await getProducts();

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-6xl">

        <Header
          title="Каталог товарів"
          description="Новий frontend підключений до FastAPI backend."
        />


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