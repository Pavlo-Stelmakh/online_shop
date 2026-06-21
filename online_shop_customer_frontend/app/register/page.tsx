import Link from "next/link";

export default function RegisterPage() {
  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Клієнтська панель online shop</p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Реєстрація</h1>
      </div>

      <div className="space-y-6 rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
        <p className="text-lg text-slate-700">Реєстрація буде додана на наступному етапі.</p>
        <Link
          href="/"
          className="inline-flex rounded-full bg-slate-950 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          Повернутися до каталогу
        </Link>
      </div>
    </section>
  );
}
