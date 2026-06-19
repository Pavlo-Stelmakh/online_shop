import type { CartItem, Product } from "@/types";

const CART_KEY = "online_shop_cart";

export function getCart(): CartItem[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(CART_KEY) ?? "[]") as CartItem[]; } catch { return []; }
}

export function saveCart(items: CartItem[]) {
  localStorage.setItem(CART_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("cart-changed"));
}

export function addProductToCart(product: Product, quantity = 1) {
  const items = getCart();
  const existing = items.find((item) => item.productId === product.id);
  const stock = product.stock;
  if (existing) {
    existing.quantity = Math.min(existing.quantity + quantity, stock ?? existing.quantity + quantity);
  } else {
    items.push({ productId: product.id, name: product.name, unitPrice: product.price, priceAmount: product.price_amount, imageUrl: product.image_url, stock, quantity: Math.min(quantity, stock ?? quantity) });
  }
  saveCart(items);
}

export function formatPrice(value: number, amount?: string) { return `${amount ?? value.toFixed(2)} ₴`; }
export function cartTotal(items: CartItem[]) { return items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0); }
