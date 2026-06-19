import ProductCard from "@/components/ProductCard";
import { api } from "@/lib/api";

export default async function Home() {
  try {
    const catalog = await api.getProducts();
    return <div><div className="mb-8"><h1 className="text-3xl font-bold">Каталог товарів</h1><p className="mt-2 text-slate-600">Оберіть товари та додайте їх до кошика.</p></div>{catalog.items.length === 0 ? <div className="rounded-xl bg-white p-8 text-center text-slate-600">Каталог поки порожній.</div> : <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">{catalog.items.map((product) => <ProductCard key={product.id} product={product} />)}</div>}</div>;
  } catch (error) {
    return <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">Не вдалося завантажити каталог. Сервер може бути тимчасово недоступний.</div>;
  }
}
