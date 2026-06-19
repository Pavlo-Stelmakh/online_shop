"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { api } from "@/lib/api";
import { setAccessToken } from "@/lib/auth";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const data = new FormData(event.currentTarget);

    try {
      const token = await api.login(String(data.get("username")), String(data.get("password")));
      setAccessToken(token.access_token);
      router.push(params.get("next") ?? "/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Помилка входу");
    } finally {
      setLoading(false);
    }
  }

  return <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-2xl bg-white p-6 shadow"><h1 className="text-2xl font-bold">Вхід</h1>{error && <p className="rounded bg-red-50 p-3 text-red-700">{error}</p>}<input required name="username" placeholder="Імʼя користувача" className="w-full rounded border p-3" /><input required name="password" type="password" placeholder="Пароль" className="w-full rounded border p-3" /><button disabled={loading} className="w-full rounded bg-blue-600 p-3 text-white disabled:bg-slate-300">{loading ? "Входимо..." : "Увійти"}</button><p className="text-sm">Немає акаунта? <Link className="text-blue-700" href="/register">Зареєструватися</Link></p></form>;
}

export default function LoginPage() {
  return <Suspense fallback={<div className="mx-auto max-w-md rounded-2xl bg-white p-6 shadow">Завантаження...</div>}><LoginForm /></Suspense>;
}
