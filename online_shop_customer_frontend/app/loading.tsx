export default function Loading() {
  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Клієнтська панель online shop
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Каталог</h1>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
        <p className="text-lg text-slate-700">Завантажуємо товари…</p>
      </div>
    </section>
  );
}
