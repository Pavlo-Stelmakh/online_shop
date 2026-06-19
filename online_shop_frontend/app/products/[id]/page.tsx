import ProductCard from "@/components/ProductCard";
import { api } from "@/lib/api";

export default async function ProductDetails({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const product = await api.getProduct(Number(id));
    return <div className="grid gap-8 md:grid-cols-2"><div className="flex min-h-96 items-center justify-center rounded-2xl bg-slate-100">{product.image_url ? <img src={product.image_url} alt={product.name} className="max-h-[520px] rounded-2xl object-contain" /> : <span className="text-slate-500">Немає фото</span>}</div><div><h1 className="text-3xl font-bold">{product.name}</h1><p className="mt-4 whitespace-pre-line text-slate-700">{product.description}</p><div className="mt-6"><ProductCard product={product} /></div></div></div>;
  } catch { return <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">Товар не знайдено або сервер недоступний.</div>; }
}
