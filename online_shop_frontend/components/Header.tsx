"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { clearAccessToken, getAccessToken } from "@/lib/auth";

export default function Header() {
  const [loggedIn, setLoggedIn] = useState(false);
  useEffect(() => {
    const refresh = () => setLoggedIn(Boolean(getAccessToken()));
    refresh();
    window.addEventListener("auth-changed", refresh);
    return () => window.removeEventListener("auth-changed", refresh);
  }, []);
  return <header className="border-b bg-white"><nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4"><Link className="text-xl font-bold text-slate-900" href="/">Online Shop</Link><div className="flex items-center gap-4 text-sm font-medium"><Link href="/">Каталог</Link><Link href="/cart">Кошик</Link>{loggedIn ? <button onClick={clearAccessToken} className="rounded bg-slate-900 px-3 py-2 text-white">Вийти</button> : <><Link href="/login">Вхід</Link><Link className="rounded bg-blue-600 px-3 py-2 text-white" href="/register">Реєстрація</Link></>}</div></nav></header>;
}
