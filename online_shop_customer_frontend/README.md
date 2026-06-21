# Online Shop Customer Frontend

Customer-facing Next.js application for browsing the online shop catalog and managing a local cart.

## Catalog API

The catalog page reads products from the backend `GET /products` endpoint. The API base URL is configured with `NEXT_PUBLIC_API_BASE_URL`.

If `NEXT_PUBLIC_API_BASE_URL` is not set, the app falls back to:

```text
https://online-shop-api-z9y4.onrender.com
```

Example local environment value:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Current scope

The customer frontend currently displays the product catalog and provides a client-side cart stored in `localStorage` under `online_shop_customer_cart`. Checkout, authentication, and backend order creation flows are still not implemented.
