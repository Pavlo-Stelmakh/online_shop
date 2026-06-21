export type CartItem = {
  id: number;
  name: string;
  description?: string;
  price: number;
  price_amount?: string;
  image_url?: string | null;
  stock: number;
  quantity: number;
};

const CART_STORAGE_KEY = "online_shop_customer_cart";

type CartProduct = Omit<CartItem, "quantity">;

function isBrowser() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function normalizePositiveInteger(value: unknown, fallback = 0) {
  const numberValue = Number(value);

  if (!Number.isFinite(numberValue)) {
    return fallback;
  }

  return Math.max(0, Math.floor(numberValue));
}

function normalizeCartItem(item: unknown): CartItem | null {
  if (!item || typeof item !== "object") {
    return null;
  }

  const candidate = item as Partial<CartItem>;
  const id = normalizePositiveInteger(candidate.id);
  const name = typeof candidate.name === "string" ? candidate.name : "";
  const price = Number(candidate.price);
  const stock = normalizePositiveInteger(candidate.stock);
  const quantity = normalizePositiveInteger(candidate.quantity, 1);

  if (!id || !name || !Number.isFinite(price) || price < 0 || stock <= 0) {
    return null;
  }

  return {
    id,
    name,
    description: typeof candidate.description === "string" ? candidate.description : undefined,
    price,
    price_amount: typeof candidate.price_amount === "string" ? candidate.price_amount : undefined,
    image_url: typeof candidate.image_url === "string" || candidate.image_url === null ? candidate.image_url : undefined,
    stock,
    quantity: Math.min(Math.max(quantity, 1), stock),
  };
}

function getItemPrice(item: Pick<CartItem, "price" | "price_amount">) {
  const priceAmount = item.price_amount ? Number(item.price_amount) : Number.NaN;

  return Number.isFinite(priceAmount) ? priceAmount : item.price;
}

export function getCart(): CartItem[] {
  if (!isBrowser()) {
    return [];
  }

  try {
    const storedCart = window.localStorage.getItem(CART_STORAGE_KEY);

    if (!storedCart) {
      return [];
    }

    const parsedCart = JSON.parse(storedCart) as unknown;

    if (!Array.isArray(parsedCart)) {
      return [];
    }

    return parsedCart.map(normalizeCartItem).filter((item): item is CartItem => item !== null);
  } catch {
    return [];
  }
}

export function saveCart(cart: CartItem[]) {
  if (!isBrowser()) {
    return;
  }

  const normalizedCart = cart.map(normalizeCartItem).filter((item): item is CartItem => item !== null);
  window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(normalizedCart));
}

export function addToCart(product: CartProduct) {
  if (product.stock <= 0) {
    return getCart();
  }

  const cart = getCart();
  const existingItem = cart.find((item) => item.id === product.id);

  if (existingItem) {
    existingItem.quantity = Math.min(existingItem.quantity + 1, existingItem.stock);
  } else {
    cart.push({ ...product, quantity: 1 });
  }

  saveCart(cart);
  return cart;
}

export function removeFromCart(productId: number) {
  const cart = getCart().filter((item) => item.id !== productId);
  saveCart(cart);
  return cart;
}

export function updateCartItemQuantity(productId: number, quantity: number) {
  const cart = getCart().map((item) => {
    if (item.id !== productId) {
      return item;
    }

    return {
      ...item,
      quantity: Math.min(Math.max(Math.floor(quantity), 1), item.stock),
    };
  });

  saveCart(cart);
  return cart;
}

export function clearCart() {
  saveCart([]);
}

export function getCartTotal() {
  return getCart().reduce((total, item) => total + getItemPrice(item) * item.quantity, 0);
}

export function getCartItemsCount() {
  return getCart().reduce((count, item) => count + item.quantity, 0);
}
