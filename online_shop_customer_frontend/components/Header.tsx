"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CART_UPDATED_EVENT, getCartItemsCount } from "../lib/cart";

const navigation = [
  { label: "Каталог", href: "/" },
  { label: "Кошик", href: "/cart" },
  { label: "Вхід", href: "/login" },
  { label: "Реєстрація", href: "/register" },
];

export function Header() {
  const [cartItemsCount, setCartItemsCount] = useState(0);

  useEffect(() => {
    function updateCartItemsCount() {
      setCartItemsCount(getCartItemsCount());
    }

    updateCartItemsCount();
    window.addEventListener(CART_UPDATED_EVENT, updateCartItemsCount);
    window.addEventListener("storage", updateCartItemsCount);

    return () => {
      window.removeEventListener(CART_UPDATED_EVENT, updateCartItemsCount);
      window.removeEventListener("storage", updateCartItemsCount);
    };
  }, []);

  return (
    <header className="border-b border-slate-200 bg-white/90 shadow-sm backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <Link href="/" className="text-xl font-bold tracking-tight text-slate-950">
          Online Shop
        </Link>

        <nav aria-label="Головна навігація" className="flex flex-wrap items-center gap-2 sm:gap-4">
          {navigation.map((item) => {
            const label = item.href === "/cart" && cartItemsCount > 0 ? `${item.label} (${cartItemsCount})` : item.label;

            return (
              <Link
                key={item.label}
                href={item.href}
                className="rounded-full px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-950"
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
