"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { setAccessToken } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter(); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setLoading(true); setError(""); const data = new FormData(event.currentTarget); const username = String(data.get("username")); const password = String(data.get("password")); try { await api.register({ username, email: String(data.get("email")), password }); const token = await api.login(username, password); setAccessToken(token.access_token); router.push("/"); } catch (e) { setError(e instanceof Error ? e.message : "Помилка реєстрації"); } finally { setLoading(false); } }
  return <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-2xl bg-white p-6 shadow"><h1 className="text-2xl font-bold">Реєстрація</h1>{error && <p className="rounded bg-red-50 p-3 text-red-700">{error}</p>}<input required name="username" placeholder="Імʼя користувача" className="w-full rounded border p-3" /><input required name="email" type="email" placeholder="Email" className="w-full rounded border p-3" /><input required name="password" type="password" minLength={6} placeholder="Пароль" className="w-full rounded border p-3" /><button disabled={loading} className="w-full rounded bg-blue-600 p-3 text-white disabled:bg-slate-300">{loading ? "Створюємо..." : "Зареєструватися"}</button></form>;
}
