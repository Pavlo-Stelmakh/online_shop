# Online Shop Frontend

Clean customer storefront MVP for the existing FastAPI `online_shop` backend.

## Clean storefront quick start

```bash
cd online_shop_frontend
npm install
npm run dev
npm run build
```

Create `.env.local` with the backend URL:

```bash
NEXT_PUBLIC_API_BASE_URL=https://online-shop-api-z9y4.onrender.com
```

## MVP scope

- Route `/` fetches `GET /products` client-side and renders the Ukrainian catalog.
- Product data is normalized in one helper before cart validation.
- Cart data is stored in browser `localStorage` only from client components.
- Route `/cart` supports quantity changes up to stock, item removal, and clearing the cart.
- Routes `/login` and `/register` keep simple forms and store the token client-side.
- Route `/checkout` is intentionally minimal and ready for a future order creation step.
