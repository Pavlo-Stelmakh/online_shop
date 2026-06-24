import type { Product } from "@/types";

const CART_STORAGE_KEY = "online_shop_cart";

export type CartItem = {
  product: Product;
  quantity: number;
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getCartItems(): CartItem[] {
  if (!isBrowser()) {
    return [];
  }

  const rawCart = window.localStorage.getItem(CART_STORAGE_KEY);

  if (!rawCart) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawCart);

    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed;
  } catch {
    return [];
  }
}

export function saveCartItems(items: CartItem[]): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
}

export function addToCart(product: Product): CartItem[] {
  const items = getCartItems();
  const existingItem = items.find((item) => item.product.id === product.id);

  let nextItems: CartItem[];

  if (existingItem) {
    nextItems = items.map((item) => {
      if (item.product.id !== product.id) {
        return item;
      }

      return {
        ...item,
        quantity: Math.min(item.quantity + 1, product.stock),
      };
    });
  } else {
    nextItems = [
      ...items,
      {
        product,
        quantity: 1,
      },
    ];
  }

  saveCartItems(nextItems);
  return nextItems;
}

export function updateCartItemQuantity(productId: number, quantity: number): CartItem[] {
  const items = getCartItems();

  const nextItems = items
    .map((item) => {
      if (item.product.id !== productId) {
        return item;
      }

      return {
        ...item,
        quantity: Math.min(Math.max(quantity, 1), item.product.stock),
      };
    })
    .filter((item) => item.quantity > 0);

  saveCartItems(nextItems);
  return nextItems;
}

export function removeFromCart(productId: number): CartItem[] {
  const nextItems = getCartItems().filter((item) => item.product.id !== productId);
  saveCartItems(nextItems);
  return nextItems;
}

export function clearCart(): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(CART_STORAGE_KEY);
}

export function getCartTotal(items: CartItem[]): number {
  return items.reduce((total, item) => {
    return total + item.product.price * item.quantity;
  }, 0);
}

export function getCartItemsCount(items: CartItem[]): number {
  return items.reduce((total, item) => {
    return total + item.quantity;
  }, 0);
}