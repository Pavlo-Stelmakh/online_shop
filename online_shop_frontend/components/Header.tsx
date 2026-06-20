"use client";

import Link from "next/link";

export default function Header() {
  return (
    <header className="border-b bg-white">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link className="text-xl font-bold text-slate-900" href="/">
          Online Shop
        </Link>
        <div className="flex items-center gap-4 text-sm font-medium">
          <Link href="/">Каталог</Link>
          <Link href="/cart">Кошик</Link>
          <Link href="/login">Вхід</Link>
          <Link className="rounded bg-blue-600 px-3 py-2 text-white" href="/register">
            Реєстрація
          </Link>
        </div>
      </nav>
    </header>
  );
}
