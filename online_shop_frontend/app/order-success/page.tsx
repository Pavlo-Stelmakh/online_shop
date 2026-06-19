import Link from "next/link";

export default function OrderSuccessPage() {
  return <div className="mx-auto max-w-xl rounded-2xl bg-white p-8 text-center shadow"><h1 className="text-3xl font-bold text-green-700">Ваше замовлення успішно створено.</h1><p className="mt-3 text-slate-600">Ми передали його в адміністративну панель для обробки.</p><Link className="mt-6 inline-block rounded bg-blue-600 px-5 py-3 text-white" href="/">Повернутися до каталогу</Link></div>;
}
