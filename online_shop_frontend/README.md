# Online Shop Frontend

Customer-facing storefront MVP for the existing FastAPI `online_shop` backend.

## Install

```bash
cd online_shop_frontend
npm install
```

## Environment setup

Create `.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=https://online-shop-api-z9y4.onrender.com
```

A default example is included in `.env.example`.

## Local run

```bash
npm run dev
```

Open http://localhost:3000.

## Build

```bash
npm run build
```

## Vercel deploy

1. Import `online_shop_frontend` as the project root in Vercel.
2. Set `NEXT_PUBLIC_API_BASE_URL` to the backend URL.
3. Deploy with the default Next.js framework preset.

## Backend endpoints used

- `GET /products` for the catalog envelope (`items`, `total`, `skip`, `limit`, `sort_by`, `sort_order`).
- `GET /products/{id}` for product details.
- `POST /auth/register` for customer registration.
- `POST /auth/login` for token login.
- `GET /auth/me` for current user support.
- `GET /customers/me` to find the customer profile for checkout.
- `POST /customers` to create a customer profile when one does not exist.
- `POST /orders` with `Authorization: Bearer <token>` to create orders.

## Current MVP limitations and backend follow-ups

- The MVP stores the access token and cart in `localStorage`; use secure cookies/session hardening before production.
- Checkout creates a customer profile only when `GET /customers/me` returns 404. If a profile exists, the form does not update it.
- Product stock is enforced client-side only from the last known catalog/detail response; backend remains the source of truth during order creation.
- The storefront assumes CORS is enabled for the deployed frontend domain.
