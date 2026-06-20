"use client";

import { FormEvent, useState } from "react";
import { apiUrl } from "@/lib/api";

export default function RegisterPage() {
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setMessage(null);

    const formData = new FormData(event.currentTarget);
    const payload = {
      username: formData.get("username"),
      email: formData.get("email"),
      password: formData.get("password"),
    };

    try {
      const response = await fetch(apiUrl("/auth/register"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error("Помилка реєстрації");
      }
      setMessage("Реєстрація успішна. Тепер увійдіть у свій акаунт.");
      event.currentTarget.reset();
    } catch {
      setMessage("Не вдалося зареєструватися. Спробуйте інші дані.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-sm">
      <h1 className="text-3xl font-bold text-slate-950">Реєстрація</h1>
      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700">Імʼя користувача<input className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" name="username" required type="text" /></label>
        <label className="block text-sm font-medium text-slate-700">Email<input className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" name="email" required type="email" /></label>
        <label className="block text-sm font-medium text-slate-700">Пароль<input className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" name="password" required type="password" /></label>
        <button className="w-full rounded-xl bg-slate-950 px-4 py-2 font-semibold text-white hover:bg-slate-800 disabled:opacity-60" disabled={isLoading} type="submit">{isLoading ? "Реєстрація..." : "Зареєструватися"}</button>
      </form>
      {message && <p className="mt-4 text-sm text-slate-700">{message}</p>}
    </section>
  );
}
