"use client";

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

  useEffect(() => {
    setCartItems(getCart());
  }, []);

  const cartTotal = cartItems.reduce((total, item) => total + getDisplayPrice(item) * item.quantity, 0);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
        <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div>
            <label htmlFor="customer-name" className="block text-sm font-semibold text-slate-700">
              Ім’я
            </label>
            <input
              id="customer-name"
              name="customerName"
              type="text"
              required
              placeholder="Введіть ваше ім’я"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-950"
            />
          </div>

          <div>
            <label htmlFor="customer-phone" className="block text-sm font-semibold text-slate-700">
              Телефон
            </label>
            <input
              id="customer-phone"
              name="customerPhone"
              type="tel"
              required
              placeholder="Введіть номер телефону"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-950"
            />
          </div>

          <div>
            <label htmlFor="delivery-address" className="block text-sm font-semibold text-slate-700">
              Адреса доставки
            </label>
            <input
              id="delivery-address"
              name="deliveryAddress"
              type="text"
              required
              placeholder="Місто, вулиця, будинок, квартира"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-950 outline-none transition focus:border-slate-950"
            />
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
