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
- Checkout creates an authenticated backend order from the current `localStorage` cart, clears the cart after success, and shows a success state with a link back to the catalog.
- Checkout requires an existing customer profile for the logged-in user because the backend order schema requires `customer_id`.
- Payment and delivery flows are not implemented yet; the MVP only creates the order in the backend.
