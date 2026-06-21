import Link from "next/link";

const navigation = [
  { label: "Каталог", href: "/" },
  { label: "Кошик", href: "#" },
  { label: "Вхід", href: "#" },
  { label: "Реєстрація", href: "#" },
];

export function Header() {
  return (
    <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <Link href="/" className="text-xl font-bold text-slate-950">Online Shop</Link>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          {navigation.map((item) => (
            <Link key={item.label} href={item.href} className="rounded-full px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-950">
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
