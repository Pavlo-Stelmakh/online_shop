import type { CartItem, Product } from "@/types";

const CART_STORAGE_KEY = "online_shop_cart";

function canUseStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getCart(): CartItem[] {
  if (!canUseStorage()) {
    return [];
  }

  const rawCart = window.localStorage.getItem(CART_STORAGE_KEY);
  if (!rawCart) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawCart) as CartItem[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveCart(cart: CartItem[]) {
  if (canUseStorage()) {
    window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
  }
}

export function addToCart(product: Product) {
  const cart = getCart();
  const existingItem = cart.find((item) => item.id === product.id);

  if (existingItem) {
    existingItem.quantity = Math.min(existingItem.quantity + 1, product.stock);
    existingItem.stock = product.stock;
  } else {
    cart.push({ ...product, quantity: 1 });
  }

  saveCart(cart);
  return cart;
}

export function clearCart() {
  saveCart([]);
}
