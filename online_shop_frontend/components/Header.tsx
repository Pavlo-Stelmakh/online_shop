import Link from "next/link";

const links = [
  { href: "/", label: "Каталог" },
  { href: "/cart", label: "Кошик" },
  { href: "/login", label: "Вхід" },
  { href: "/register", label: "Реєстрація" },
];

export function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between">
        <Link className="text-2xl font-bold text-slate-950" href="/">
          Online Shop
        </Link>
        <div className="flex flex-wrap gap-3 text-sm font-medium text-slate-700">
          {links.map((link) => (
            <Link className="rounded-full px-3 py-2 hover:bg-slate-100 hover:text-slate-950" href={link.href} key={link.href}>
              {link.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
