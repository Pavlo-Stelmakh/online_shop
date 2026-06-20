import type { CartItem, Product } from "@/types";
import { isProductValidForCart } from "@/lib/products";

const CART_KEY = "online_shop_cart";

export function getCart(): CartItem[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem(CART_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveCart(items: CartItem[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(CART_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("cart-changed"));
}


export function addProductToCart(product: Product) {
  console.log("ADD TO CART CLICKED", product);

  const productId = Number(product.id);
  const stock = Number(product.stock);
  const unitPrice = Number(product.price);

  if (!Number.isFinite(productId) || productId <= 0) {
    alert("Помилка: товар має неправильний ID");
    return;
  }

  if (!Number.isFinite(stock) || stock <= 0) {
    alert("Цього товару немає в наявності");
    return;
  }

  const items = getCart();
  const existing = items.find((item) => item.productId === productId);

  if (existing) {
    existing.quantity = Math.min(existing.quantity + 1, stock);
    existing.stock = stock;
    existing.unitPrice = Number.isFinite(unitPrice) ? unitPrice : 0;
    existing.priceAmount = product.priceAmount;
  } else {
    items.push({
      productId,
      name: product.name,
      description: product.description,
      unitPrice: Number.isFinite(unitPrice) ? unitPrice : 0,
      priceAmount: product.priceAmount,
      imageUrl: product.imageUrl,
      stock,
      quantity: 1,
    });
  }

  saveCart(items);
  alert("Товар додано в кошик");
}


export function formatPrice(value: number, amount?: string) {
  const display = amount ?? (Number.isFinite(value) ? value.toFixed(2) : "0.00");
  return `${display} ₴`;
}

export function cartTotal(items: CartItem[]) {
  return items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
}
