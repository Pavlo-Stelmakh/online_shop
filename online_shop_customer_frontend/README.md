# Online Shop Customer Frontend

Customer-facing Next.js application for browsing the online shop catalog, managing a local cart, and viewing a checkout UI.

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

The customer frontend currently displays the product catalog and provides a client-side cart stored in `localStorage` under `online_shop_customer_cart`. A checkout page exists as UI only: it reads the local cart and collects delivery/contact details, but backend order creation is still not implemented. Authentication, login, and registration flows are still not implemented.
