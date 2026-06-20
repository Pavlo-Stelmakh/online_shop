"use client";

import { useEffect, useState } from "react";
import ProductCard from "@/components/ProductCard";
import { api } from "@/lib/api";
import { normalizeProduct } from "@/lib/products";
import type { Product } from "@/types";

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadProducts() {
      try {
        const catalog = await api.getProducts();
        if (active) setProducts(catalog.items.map(normalizeProduct));
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Не вдалося завантажити каталог.");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadProducts();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Каталог товарів</h1>
        <p className="mt-2 text-slate-600">Оберіть товари та додайте їх до кошика.</p>
      </div>

      {loading && <div className="rounded-xl bg-white p-8 text-center text-slate-600">Завантажуємо товари...</div>}
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">{error}</div>}
      {!loading && !error && products.length === 0 && <div className="rounded-xl bg-white p-8 text-center text-slate-600">Каталог поки порожній.</div>}
      {!loading && !error && products.length > 0 && (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product, index) => (
            <ProductCard key={Number.isFinite(product.id) ? product.id : `invalid-${index}`} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}
