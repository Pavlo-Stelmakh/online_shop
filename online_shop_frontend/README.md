# Online Shop Frontend

Clean minimal customer storefront MVP built with Next.js, TypeScript, Tailwind CSS, App Router, client-side catalog fetching, and a `localStorage` cart.

## Setup

```bash
npm install
```

Create a local environment file if needed:

```bash
NEXT_PUBLIC_API_BASE_URL=https://online-shop-api-z9y4.onrender.com
```

## Development

```bash
npm run dev
```

Open the storefront at http://localhost:3000.

## Production build

```bash
npm run build
```

## Notes

- The backend API and Ukrainian admin panel are separate applications.
- This frontend only reads products, handles auth token storage, and manages the cart in the browser.
- Checkout currently shows an order summary placeholder and does not create backend orders.
