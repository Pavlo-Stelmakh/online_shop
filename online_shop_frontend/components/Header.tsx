"use client";

import Link from "next/link";
import { useState } from "react";
import { getCurrentUser, logout, type CurrentUser } from "@/lib/auth";

type HeaderProps = {
  title: string;
  description?: string;
};

export default function Header({ title, description }: HeaderProps) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  async function handleCheckUser() {
    const currentUser = await getCurrentUser();
    setUser(currentUser);
    setIsLoaded(true);
  }

  function handleLogout() {
    logout();
    setUser(null);
    setIsLoaded(true);
  }

  return (
    <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
        {description && <p className="mt-2 text-gray-600">{description}</p>}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Link href="/" className="rounded-lg border border-gray-300 px-4 py-2 text-gray-800">
          Каталог
        </Link>

        <Link href="/orders" className="rounded-lg border border-gray-300 px-4 py-2 text-gray-800">
          Мої замовлення
        </Link>
        
        <Link href="/cart" className="rounded-lg border border-gray-300 px-4 py-2 text-gray-800">
          Кошик
        </Link>

        {!isLoaded && (
          <button
            type="button"
            onClick={handleCheckUser}
            className="rounded-lg border border-gray-300 px-4 py-2 text-gray-800"
          >
            Перевірити вхід
          </button>
        )}

        {isLoaded && user && (
          <>
            <span className="rounded-lg bg-green-50 px-4 py-2 text-sm text-green-700">
              {user.username} / {user.role}
            </span>

            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg bg-black px-4 py-2 text-white"
            >
              Вийти
            </button>
          </>
        )}

        {isLoaded && !user && (
          <Link href="/login" className="rounded-lg bg-black px-4 py-2 text-white">
            Увійти
          </Link>
        )}
      </div>
    </header>
  );
}