export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "https://online-shop-api-z9y4.onrender.com";

export function apiUrl(path: string) {
  const baseUrl = API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  return `${baseUrl}${normalizedPath}`;
}
