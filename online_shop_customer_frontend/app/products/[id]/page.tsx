import Link from "next/link";

import { getProduct } from "../../../lib/products";
import { ProductDetails } from "./ProductDetails";

export const dynamic = "force-dynamic";

type ProductPageProps = {
  params: {
    id: string;
  };
};

export default async function ProductPage({ params }: ProductPageProps) {
  const productId = Number(params.id);
  const product = Number.isFinite(productId) ? await getProduct(productId) : null;

  if (!product) {
    return (
      <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
        <p className="text-lg font-medium text-slate-700">Товар не знайдено.</p>
        <Link href="/" className="inline-flex text-sm font-semibold text-slate-700 transition hover:text-slate-950">
          Повернутися до каталогу
        </Link>
      </section>
    );
  }

  return <ProductDetails product={product} />;
}
