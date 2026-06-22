"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { getCart, type CartItem } from "../../lib/cart";

function getDisplayPrice(item: CartItem) {
  const priceAmount = item.price_amount ? Number(item.price_amount) : item.price;

  return Number.isFinite(priceAmount) ? priceAmount : item.price;
}

function formatPrice(price: number) {
  return `${price.toFixed(2)} грн`;
}

export default function CheckoutPage() {
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [successMessage, setSuccessMessage] = useState("");
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    setCartItems(getCart());
  }, []);

  const cartTotal = cartItems.reduce((total, item) => total + getDisplayPrice(item) * item.quantity, 0);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const errors: Record<string, string> = {};

    if (!String(formData.get("customerName") ?? "").trim()) {
      errors.customerName = "Введіть прізвище та ім’я.";
    }

    if (!String(formData.get("customerEmail") ?? "").trim()) {
      errors.customerEmail = "Введіть електронну пошту.";
    }

    if (!String(formData.get("customerPhone") ?? "").trim()) {
      errors.customerPhone = "Введіть номер телефону.";
    }

    if (!String(formData.get("deliveryAddress") ?? "").trim()) {
      errors.deliveryAddress = "Введіть адресу доставки.";
    }

    setValidationErrors(errors);

    if (Object.keys(errors).length > 0) {
      setSuccessMessage("");
      return;
    }

    setSuccessMessage("Форма оформлення готова. Надсилання замовлення буде додано на наступному етапі.");
  }

  if (cartItems.length === 0) {
    return (
      <section className="space-y-8">
        <div className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Клієнтська панель online shop</p>
          <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Оформлення замовлення</h1>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
          <p className="text-lg text-slate-700">Кошик порожній. Додайте товари перед оформленням замовлення.</p>
          <Link
            href="/"
            className="mt-6 inline-flex rounded-full bg-slate-950 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Повернутися до каталогу
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Клієнтська панель online shop</p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Оформлення замовлення</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
        <form noValidate onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div>
            <label htmlFor="customer-name" className="block text-sm font-semibold text-slate-700">
              Прізвище, ім’я
            </label>
            <input
              id="customer-name"
              name="customerName"
              type="text"
              placeholder="Введіть прізвище та ім’я"
              aria-invalid={validationErrors.customerName ? "true" : "false"}
              aria-describedby={validationErrors.customerName ? "customer-name-error" : undefined}
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-950"
            />
            {validationErrors.customerName ? (
              <p id="customer-name-error" className="mt-2 text-sm font-medium text-red-600">
                {validationErrors.customerName}
              </p>
            ) : null}
          </div>


          <div>
            <label htmlFor="customer-email" className="block text-sm font-semibold text-slate-700">
              Електронна пошта
            </label>
            <input
              id="customer-email"
              name="customerEmail"
              type="email"
              placeholder="Введіть електронну пошту"
              aria-invalid={validationErrors.customerEmail ? "true" : "false"}
              aria-describedby={validationErrors.customerEmail ? "customer-email-error" : undefined}
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-950"
            />
            {validationErrors.customerEmail ? (
              <p id="customer-email-error" className="mt-2 text-sm font-medium text-red-600">
                {validationErrors.customerEmail}
              </p>
            ) : null}
          </div>

          <div>
            <label htmlFor="customer-phone" className="block text-sm font-semibold text-slate-700">
              Телефон
            </label>
            <input
              id="customer-phone"
              name="customerPhone"
              type="tel"
              placeholder="Введіть номер телефону"
              aria-invalid={validationErrors.customerPhone ? "true" : "false"}
              aria-describedby={validationErrors.customerPhone ? "customer-phone-error" : undefined}
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-950"
            />
            {validationErrors.customerPhone ? (
              <p id="customer-phone-error" className="mt-2 text-sm font-medium text-red-600">
                {validationErrors.customerPhone}
              </p>
            ) : null}
          </div>

          <div>
            <label htmlFor="delivery-address" className="block text-sm font-semibold text-slate-700">
              Адреса доставки
            </label>
            <textarea
              id="delivery-address"
              name="deliveryAddress"
              rows={2}
              placeholder="Місто, вулиця, будинок, квартира"
              aria-invalid={validationErrors.deliveryAddress ? "true" : "false"}
              aria-describedby={validationErrors.deliveryAddress ? "delivery-address-error" : undefined}
              className="mt-2 w-full resize-none rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-950"
            />
            {validationErrors.deliveryAddress ? (
              <p id="delivery-address-error" className="mt-2 text-sm font-medium text-red-600">
                {validationErrors.deliveryAddress}
              </p>
            ) : null}
          </div>

          <div>
            <label htmlFor="order-comment" className="block text-sm font-semibold text-slate-700">
              Коментар до замовлення
            </label>
            <textarea
              id="order-comment"
              name="orderComment"
              rows={4}
              placeholder="Додайте побажання до замовлення"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-950"
            />
          </div>

          <button
            type="submit"
            className="rounded-full bg-emerald-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700"
          >
            Підтвердити оформлення
          </button>

          {successMessage ? <p className="rounded-xl bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">{successMessage}</p> : null}
        </form>

        <aside className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-bold text-slate-950">Ваше замовлення</h2>
          <div className="divide-y divide-slate-200">
            {cartItems.map((item) => {
              const price = getDisplayPrice(item);
              const lineTotal = price * item.quantity;

              return (
                <div key={item.id} className="space-y-2 py-4 first:pt-0">
                  <div className="flex items-start justify-between gap-4">
                    <h3 className="font-semibold text-slate-950">{item.name}</h3>
                    <p className="font-semibold text-slate-950">{formatPrice(lineTotal)}</p>
                  </div>
                  <p className="text-sm text-slate-600">Кількість: {item.quantity}</p>
                  <p className="text-sm text-slate-600">Ціна: {formatPrice(price)}</p>
                </div>
              );
            })}
          </div>
          <p className="border-t border-slate-200 pt-4 text-xl font-bold text-slate-950">Загальна сума: {formatPrice(cartTotal)}</p>
        </aside>
      </div>
    </section>
  );
}
