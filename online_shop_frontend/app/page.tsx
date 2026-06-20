"use client";

import { useEffect, useState } from "react";
import { ProductCard } from "@/components/ProductCard";
import { fetchProducts } from "@/lib/products";
import type { Product } from "@/types";

export default function CatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    fetchProducts()
      .then((items) => {
        if (isMounted) {
          setProducts(items);
          setError(null);
        }
      })
      .catch(() => {
        if (isMounted) {
          setError("Не вдалося завантажити каталог. Спробуйте пізніше.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-950">Каталог</h1>
        <p className="mt-2 text-slate-600">Оберіть товари та додайте їх у кошик.</p>
      </div>

      {isLoading && <p className="rounded-2xl bg-white p-6 text-slate-600">Завантаження товарів...</p>}
      {error && <p className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-700">{error}</p>}
      {!isLoading && !error && products.length === 0 && (
        <p className="rounded-2xl bg-white p-6 text-slate-600">Каталог порожній</p>
      )}
      {!isLoading && !error && products.length > 0 && (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </section>
  );
}
