const TOKEN_STORAGE_KEY = "online_shop_access_token";

function canUseStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getAccessToken() {
  if (!canUseStorage()) {
    return null;
  }

  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function saveAccessToken(token: string) {
  if (canUseStorage()) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}
