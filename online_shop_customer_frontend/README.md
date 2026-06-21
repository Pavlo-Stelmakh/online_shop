# Online Shop Customer Frontend

Customer-facing storefront for Online Shop with a Ukrainian UI.

## Catalog API

The catalog page reads real products from the backend `GET /products` endpoint. The response can be either a raw product array or an envelope with an `items` array.

Configure the backend base URL with:

```bash
NEXT_PUBLIC_API_BASE_URL=https://online-shop-api-z9y4.onrender.com
```

If `NEXT_PUBLIC_API_BASE_URL` is not set, the app falls back to `https://online-shop-api-z9y4.onrender.com`.

## Current scope

Implemented:

- Header and customer catalog page.
- Product cards populated from `GET /products`.

Not implemented yet:

- Cart.
- Authentication/login/register.
- Checkout.
