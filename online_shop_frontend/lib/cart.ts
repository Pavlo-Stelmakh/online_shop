import type { CartItem, Product } from "@/types";

const CART_KEY = "online_shop_cart";

export function isValidProductId(id: Product["id"]): id is number {
  return Number.isInteger(id) && id > 0;
}

export function canAddProductToCart(product: Product) {
  return isValidProductId(product.id) && product.stock > 0;
}

export function getCart(): CartItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(CART_KEY) ?? "[]") as CartItem[];
  } catch {
    return [];
  }
}

export function saveCart(items: CartItem[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(CART_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("cart-changed"));
}

export function addProductToCart(product: Product, quantity = 1) {
  if (!canAddProductToCart(product) || quantity < 1) return;

  const items = getCart();
  const existing = items.find((item) => item.productId === product.id);
  const quantityToAdd = Math.min(quantity, product.stock);

  if (existing) {
    existing.quantity = Math.min(existing.quantity + quantityToAdd, product.stock);
  } else {
    items.push({ productId: product.id, name: product.name, unitPrice: product.price, priceAmount: product.price_amount, imageUrl: product.image_url, stock: product.stock, quantity: quantityToAdd });
  }

  saveCart(items);
}

export function formatPrice(value: number, amount?: string) { return `${amount ?? value.toFixed(2)} ₴`; }
export function cartTotal(items: CartItem[]) { return items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0); }
