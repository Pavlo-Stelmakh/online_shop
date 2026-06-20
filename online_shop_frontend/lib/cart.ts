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
  if (!isProductValidForCart(product)) return;

  const items = getCart();
  const existing = items.find((item) => item.productId === product.id);

  if (existing) {
    existing.quantity = Math.min(existing.quantity + 1, product.stock);
    existing.stock = product.stock;
    existing.unitPrice = product.price;
    existing.priceAmount = product.priceAmount;
  } else {
    items.push({
      productId: product.id,
      name: product.name,
      description: product.description,
      unitPrice: product.price,
      priceAmount: product.priceAmount,
      imageUrl: product.imageUrl,
      stock: product.stock,
      quantity: 1,
    });
  }

  saveCart(items);
}

export function formatPrice(value: number, amount?: string) {
  const display = amount ?? (Number.isFinite(value) ? value.toFixed(2) : "0.00");
  return `${display} ₴`;
}

export function cartTotal(items: CartItem[]) {
  return items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
}
