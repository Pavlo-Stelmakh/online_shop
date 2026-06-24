"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setErrorMessage("");
    setSuccessMessage("");
    setIsLoading(true);

    try {
      await login(username, password);
      setSuccessMessage("Вхід виконано успішно.");
      setUsername("");
      setPassword("");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Помилка входу");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-md">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Вхід</h1>
          <p className="mt-2 text-gray-600">
            Увійдіть як customer або admin.
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
        >
          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="mb-1 block text-sm font-medium text-gray-700">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
                required
              />
            </div>
          </div>

          {errorMessage && (
            <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {errorMessage}
            </p>
          )}

          {successMessage && (
            <p className="mt-4 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700">
              {successMessage}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="mt-5 w-full rounded-lg bg-black px-4 py-2 text-white disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            {isLoading ? "Вхід..." : "Увійти"}
          </button>
        </form>

        <Link href="/" className="mt-5 inline-block text-sm font-medium text-gray-700">
          ← До каталогу
        </Link>
      </div>
    </main>
  );
}