# Online Shop API

![Run API Tests](https://github.com/Pavlo-Stelmakh/online_shop/actions/workflows/tests.yml/badge.svg)

## Project Overview

Online Shop API is a backend e-commerce project built with FastAPI.

The project demonstrates a production-style API with authentication, role-based access control, product catalog management, order processing, stock protection, validation rules, automated tests, CI checks and deployment to Render.

The API supports two main roles:

```text
admin
customer
```
Admin users can manage products, categories and orders. The visible admin panel interface is localized in Ukrainian, including admin templates, displayed validation messages, and order status labels. API endpoints, route paths, schemas, JSON keys, database fields, and stored order status values remain in English. The admin product UI supports listing products, opening the Add product form, creating products, editing existing products, and safely deleting products when they are not referenced by order items. The admin category UI supports listing categories, opening the Add category form, creating categories, editing categories, and safely deleting categories that are not used by products. Customer users can create orders, manage their customer profile and access their own order history.

## Live Demo
Production API:

```text
https://online-shop-api-z9y4.onrender.com
```

Swagger UI:

```text
https://online-shop-api-z9y4.onrender.com/docs
```

Admin Dashboard:

```text
https://online-shop-api-z9y4.onrender.com/admin
```


Admin Products Page:

```text
https://online-shop-api-z9y4.onrender.com/admin/products
```

Admin Add product page:

```text
https://online-shop-api-z9y4.onrender.com/admin/products/new
```


Admin Orders Page:

```text
https://online-shop-api-z9y4.onrender.com/admin/orders
```

Admin Categories Page:

```text
https://online-shop-api-z9y4.onrender.com/admin/categories
```

Admin Add category page:

```text
https://online-shop-api-z9y4.onrender.com/admin/categories/new
```

Admin Customers Page:

```text
https://online-shop-api-z9y4.onrender.com/admin/customers
```

Admin low stock page:

```text
https://online-shop-api-z9y4.onrender.com/admin/low-stock
```

The admin low stock page displays products with low stock:

Health check:

```text
https://online-shop-api-z9y4.onrender.com/health
```

## Test Status

Current automated test status:

```text
pytest -q
417 passed
```

Tests are run with:

```bash
pytest -q
```
GitHub Actions is used for CI checks on pull requests and main branch updates. CI runs `alembic upgrade head` on a temporary SQLite audit database, runs the data integrity audit against that migrated database, and then runs `pytest -q`. CI also runs a focused PostgreSQL migration/audit job with a PostgreSQL service container to verify `alembic upgrade head`, the data integrity audit script, and application import compatibility against the same database engine family used by Render production.

## Data integrity audit

Run the read-only data integrity audit before adding stricter database constraints:

```bash
python scripts/audit_data_integrity.py
```

Before running the audit, the target database must already be migrated with `alembic upgrade head`. The audit uses `DATABASE_URL`, prints a report, exits with code `0` when no problems are found, and exits with code `1` when integrity problems are detected. If the local SQLite database is empty or has not been migrated, the audit can fail with a `no such table` error.

Production precondition for the `customers.user_id -> users.id` foreign key: the audit script must return `Result: PASS` before deploy, and the `customers_user_orphan` check must be `0`. The PostgreSQL CI audit increases confidence for Render compatibility, but a production audit against the real target database is still required before deploy.


## Tech Stack

- Python
- FastAPI
- SQLAlchemy ORM
- SQLite for local development
- PostgreSQL on Render
- Alembic database migrations
- JWT authentication
- Passlib password hashing
- Pytest
- GitHub Actions
- Docker
- Render deployment

## Project Features

### Authentication and Users

- JWT authentication
- Password hashing
- Role-based access control: `admin` and `customer`
- Secure user registration: public registration always creates `customer` users
- Auth registration validates non-blank usernames, email-shaped addresses and minimum password length
- Admin-only protected routes
- User-to-customer ownership logic

### Products

- Product CRUD
- Admin UI product management at `/admin/products`, `/admin/products/new`, and `/admin/products/{product_id}/edit`; admin session authentication is required, validation errors are shown on the form, and admins can create, edit, and safely delete products. The products list shows a small preview for HTTP(S) image URLs and a fallback when no image is available. Products used in existing orders cannot be deleted.
- Product image URL support
- Product create/update validation trims product names and descriptions, requires them to be non-blank, validates positive category IDs, allows empty image URLs, requires provided image URLs to start with `http://` or `https://`, and preserves price, stock and low-stock threshold validation
- Product catalog with pagination, filtering, sorting and metadata response
- Product catalog search by name and description
- Product catalog empty search validation
- Product catalog sort validation
- Product catalog price range validation
- Admin-only low stock products endpoint

### Categories

- Category CRUD
- Admin UI category management at `/admin/categories`, `/admin/categories/new`, and `/admin/categories/{category_id}/edit`; admin session authentication is required, validation errors are shown on the form, and admins can create, edit, and safely delete unused categories
- Category create/update validation rejects blank or whitespace-only names and trims accepted names
- Category delete protection prevents deleting categories used by existing products
- Get products by category

### Customer Profiles

- Customer profile create/update validation rejects blank or whitespace-only name, email and phone values
- Customer profile email inputs must be email-shaped
- Accepted auth, customer and category string inputs are trimmed before persistence
- Invalid request schema inputs return FastAPI `422 Unprocessable Entity` responses with validation details

### Orders

- Order creation
- Order items validation and stock protection
- Duplicate product validation in order items
- Order transaction safety for multi-item orders
- Order status management with stock return on cancellation
- Customer self-service cancellation for the customer's own `new` orders via `POST /orders/{order_id}/cancel`; non-new statuses return `409 Conflict`, unknown orders return `404 Not Found`, and orders owned by another customer return `403 Forbidden`
- Customer order history
- Protected single order access
- Admin order status filtering
- Admin order customer filtering
- Admin order date filtering
- Admin order pagination
- Orders metadata response with total, skip, limit and items

### Deployment and Quality

- Basic admin dashboard UI
- Admin products page
- Admin orders page
- Admin categories page
- Admin customers page
- Admin low stock page
- Admin dashboard navigation polish
- Admin order status badges
- Admin dashboard extended stats cards
- Admin dashboard UI final polish
- Clickable dashboard cards
- Status-filtered order dashboard cards
- Admin orders filter UI
- Admin products search/filter UI
- Admin categories search UI
- Admin category create form
- Admin category update form
- Admin category delete action
- Admin customers search UI
- Product-specific low stock threshold
- Admin dashboard login authentication
- Admin test cookie warnings cleanup
- Admin product create form
- Admin product update form
- Admin product delete action
- Admin product update/delete confirmation modals
- Docker support
- GitHub Actions CI
- Render production deployment
- Automated test suite runnable with `pytest -q`


## API Overview

### Authentication

```text
POST /auth/register
POST /auth/login
GET /auth/me
```

`POST /auth/login` returns a bearer JWT `access_token` for API and Swagger authorization. Public registration always creates `customer` users; admin users are managed separately with `seed_admin.py`.

### Customers

```text
POST /customers
GET /customers/me
PUT /customers/me
```
### Categories

```text
POST /categories
GET /categories
GET /categories/{category_id}/products
PUT /categories/{category_id}
DELETE /categories/{category_id}
```
### Products

```text
GET /products
GET /products/catalog
GET /products/catalog/pages
GET /products/low-stock
POST /products
GET /products/{product_id}
PUT /products/{product_id}
DELETE /products/{product_id}
```
### Orders

```text
POST /orders
GET /orders
GET /orders/my
GET /orders/{order_id}
PUT /orders/{order_id}/status
```

Admin order detail status actions are also available in the admin UI at `/admin/orders/{order_id}`. The page shows only valid admin-only actions for the current order status: `Mark as paid` and `Cancel order` for `new` orders; `Mark as shipped` and `Cancel order` for `paid` orders; and no actions for `shipped` or `cancelled` orders. Successful status changes redirect back to the order detail page, while invalid transitions are rejected with a clear page error. Cancelling from the admin UI uses the same stock restoration logic as the order status API.

## Admin Dashboard

The project includes a basic admin dashboard UI available at:

```text
/admin
```

Admin products page:

```text
/admin/products
```

The admin products page displays a products table with:

```text
product id
name
price
stock
category id
image URL
```


Admin orders page:

```text
/admin/orders
```

The admin orders page displays an orders table with:

```text
order id
customer id
status
total price
created at
items count
```

Order IDs link to the admin order detail page:

```text
/admin/orders/{order_id}
```

The admin order detail page uses the existing admin session cookie authentication and shows:

```text
order id
customer name
customer email
status
created at
total price
order items with product name, quantity, unit price and line total
```

Unknown admin order detail URLs return `404 Not Found`. Anonymous users and non-admin users are redirected to the admin login page by the current admin UI session-auth logic.

Admin order status badges:

```text
new
paid
shipped
cancelled
```

The admin orders page displays order statuses as visual badges.

Admin categories page:

```text
/admin/categories
```

The admin categories page supports category management from the web UI. It displays a categories table with:

```text
category id
name
products count
create category form
inline edit category form
delete category form for empty categories
```

State-changing category forms use the admin UI CSRF token. Empty or duplicate category names show controlled errors, and categories with products cannot be deleted.

Admin customers page:

```text
/admin/customers
```

The admin customers page requires the existing admin session authentication and lists customer profiles. Customer IDs, customer names, and the View details action link to the admin customer detail page:

```text
/admin/customers/{customer_id}
```

The admin customer detail page shows the customer id, user id, name, email, phone, optional created_at value when the customer record has one, and the customer's related orders. Related orders include order id, status, total price, created_at, items count, and links to `/admin/orders/{order_id}`. Unknown customer detail URLs return `404 Customer not found`, while anonymous users and non-admin users are redirected to the admin login page by the admin UI session-auth logic.

Admin low stock page:

```text
/admin/low-stock
```

The admin low stock page displays products with low stock:

```text
product id
name
price
stock
category id
```


Admin navigation:

```text
Dashboard
Products
Orders
Categories
Customers
Low stock
Swagger UI
```

All admin pages use a consistent navigation structure.

Admin dashboard extended stats cards:

```text
Products
Categories
Customers
Orders
Low stock products
New Orders
Paid Orders
Shipped Orders
Cancelled Orders
```

The main admin dashboard provides overview cards for total products, categories, customers, orders, low-stock products, and order status analytics for new, paid, shipped, and cancelled orders.

The dashboard also includes recent activity sections for the latest five orders and latest five customers. Recent order IDs link to `/admin/orders/{order_id}`, and recent customer IDs/names link to `/admin/customers/{customer_id}`.

Quick action links are available for adding a product, adding a category, viewing orders, and viewing low-stock products.

Admin dashboard UI final polish:

```text
version label v4.0.0
dashboard overview description
admin pages description block
card hover effect
unified admin page footers
improved admin page descriptions
```

The admin dashboard UI was polished for a cleaner portfolio presentation.


Clickable dashboard cards:

```text
Products -> /admin/products
Categories -> /admin/categories
Customers -> /admin/customers
Orders -> /admin/orders
Low stock products -> /admin/low-stock
New Orders -> /admin/orders?status=new
Paid Orders -> /admin/orders?status=paid
Shipped Orders -> /admin/orders?status=shipped
Cancelled Orders -> /admin/orders?status=cancelled
```

Dashboard statistic cards are clickable and provide direct navigation to related admin pages and filtered order views.


Admin orders filter UI:

```text
All
New
Paid
Shipped
Cancelled
```

The admin orders page includes status filter buttons for quick navigation between all orders and status-specific order views.

Examples:

```text
/admin/orders
/admin/orders?status=new
/admin/orders?status=paid
/admin/orders?status=shipped
/admin/orders?status=cancelled
```

Admin products search/filter UI:

```text
Search
All
In Stock
Out of Stock
Reset
```

The admin products page includes search and stock filter controls for easier product catalog inspection.

Examples:

```text
/admin/products
/admin/products?search=phone
/admin/products?in_stock=true
/admin/products?in_stock=false
```

Admin categories search UI:

```text
Search
Reset
```

The admin categories page includes search controls for easier category inspection.

Examples:

```text
/admin/categories
/admin/categories?search=electronics
/admin/categories?search=phone
```

Admin customers search UI:

```text
Search
Reset
```

The admin customers page includes search controls for easier customer profile inspection.

Admin customer detail UI:

```
GET /admin/customers/{customer_id}
POST /admin/customers/{customer_id}/edit
POST /admin/customers/{customer_id}/delete
```

Admins can view customer fields, linked user ID, order links, and can edit name/email/phone with CSRF protection. Customer deletion is available only when the customer has no orders.

Search works by:

```text
name
email
phone
```

Examples:

```text
/admin/customers
/admin/customers?search=John
/admin/customers?search=example.com
/admin/customers?search=+380
```

Product-specific low stock threshold:

```text
low_stock_threshold
```

Each product has its own low stock threshold.

Low stock logic:

```text
product.stock <= product.low_stock_threshold
```

Example:

```text
stock = 8
low_stock_threshold = 10
result: low stock
```

The admin dashboard low-stock count, admin products badge styling, and `/admin/low-stock` page all use each product's individual `low_stock_threshold`.

Admin dashboard login authentication:

```text
/admin/login
/admin/logout
```

The admin dashboard UI is protected by `/admin/login` HTML form authentication. Successful admin login stores a signed, JWT-backed `admin_session` cookie with `HttpOnly`, `SameSite=Lax`, and production `Secure` settings.

Admin pages require an authenticated admin session:

```text
/admin
/admin/products
/admin/products/new
/admin/products/{product_id}/edit
/admin/orders
/admin/orders/{order_id}
/admin/categories
/admin/categories/new
/admin/categories/{category_id}/edit
/admin/customers
/admin/customers/{customer_id}
/admin/low-stock
```

Authentication uses existing users and requires:

```text
role = admin
```

API and admin UI authentication are separate flows:

| Flow | Endpoint | Credential storage | Usage |
|---|---|---|---|
| API / Swagger | `POST /auth/login` | Bearer JWT `access_token` | Authorize Swagger and API requests |
| HTML admin UI | `POST /admin/login` | Signed JWT-backed `admin_session` cookie | Access `/admin` HTML pages |

Unauthenticated users are redirected to:

```text
/admin/login
```

Admin test cookie warnings cleanup:

```text
157 passed
0 warnings
```

Admin UI tests use an authenticated admin test client instead of deprecated per-request cookie passing.


Admin product create form:

```text
/admin/products/create
```

The admin dashboard supports product creation from the web UI.

The create product form includes:

```text
name
price
description
image_url
stock
low_stock_threshold
category_id
```

After successful creation, the user is redirected back to:

```text
/admin/products
```

The form is protected by admin login authentication.


Admin product update form:

```text
/admin/products/{product_id}/edit
```

The admin dashboard supports product editing from the web UI.

The edit product form includes:

```text
name
price
description
image_url
stock
low_stock_threshold
category_id
```

After successful update, the user is redirected back to:

```text
/admin/products
```

The form is protected by admin login authentication.

Admin product delete action:

```text
POST /admin/products/{product_id}/delete
```

The admin dashboard supports safe product deletion from the web UI.

Delete behavior:

```text
products without order history can be deleted
products used in orders cannot be deleted
delete action requires confirmation
```

The delete confirmation uses a custom modal with:

```text
Cancel
Delete
```

The product edit form also uses a custom confirmation modal with:

```text
Cancel
Update
```

This helps prevent accidental product deletion or unintended product updates.

The dashboard provides a visual overview of the backend project.

Production dashboard:

```text
https://online-shop-api-z9y4.onrender.com/admin
```

## Deployment

The project is deployed on Render.

Production API:

```text
https://online-shop-api-z9y4.onrender.com
```

Swagger documentation:

```text
https://online-shop-api-z9y4.onrender.com/docs

```

Health check:

```text
https://online-shop-api-z9y4.onrender.com/health
```
Root endpoint:

```text
https://online-shop-api-z9y4.onrender.com/
```

The deployed version uses Render PostgreSQL through the `DATABASE_URL` environment variable.

Deployment stack:

| Component | Service |
|---|---|
| API hosting | Render Web Service |
| Database | Render PostgreSQL |
| Runtime | Python 3 |
| Start command | `./scripts/start.sh` |
| Build command | `pip install -r requirements.txt` |

Production startup flow:

1. Render starts `./scripts/start.sh`.
2. The script runs `alembic upgrade head` against the configured `DATABASE_URL`.
3. After migrations complete successfully, it starts FastAPI with `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`.

If you configure Render manually, use this exact Start Command:

```bash
./scripts/start.sh
```

### Render Production Deployment Checklist

Use this checklist before a controlled Render production deployment. Do not skip the production audit against the target production database.

Required Render environment variables:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Production PostgreSQL connection string used by the application runtime and Alembic migrations. |
| `SECRET_KEY` | Yes | Strong non-default value used for JWT access tokens and admin UI sessions. Must not be `fallback_secret_key`. |

Optional Render environment variables:

| Variable | Notes |
|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime override. |
| `ADMIN_SESSION_EXPIRE_SECONDS` | Admin UI session lifetime override. |
| `APP_VERSION` | Version value exposed by `/version` when configured. |
| `COMMIT_SHA` or `RENDER_GIT_COMMIT` | Commit identifier exposed by `/version` when configured. |
| `APP_ENV` / `ENVIRONMENT` | Environment marker used to identify production-like runtime. |
| `PORT` | Usually set by Render automatically; only set manually if needed. |

Pre-deploy checklist:

- Confirm Render `DATABASE_URL` points to the intended PostgreSQL database, not SQLite.
- Confirm `SECRET_KEY` is set to a strong production value and is not `fallback_secret_key`.
- Run the production data integrity audit against the target database before deploy.
- Confirm the audit output includes `Result: PASS`.
- Check the current Alembic head:

```bash
python -m alembic heads
```

- Confirm the Render Start Command is exactly:

```bash
./scripts/start.sh
```

Production audit command example:

```bash
DATABASE_URL="<production_database_url>" python scripts/audit_data_integrity.py
```

Run the production audit only from a trusted terminal and trusted logs because the command uses the production database URL. The audit is read-only, but the database must already be migrated enough for the script to run. If the audit returns `Result: FAIL`, do not deploy strict migrations until the data issues are fixed.

Deploy checklist:

- Configure Render Build Command as:

```bash
pip install -r requirements.txt
```

- Configure Render Start Command as:

```bash
./scripts/start.sh
```

- Watch Render logs during startup.
- If `alembic upgrade head` fails, `uvicorn` will not start because `scripts/start.sh` exits on errors.

Post-deploy smoke test checklist:

- `GET /`
- `GET /health`
- `GET /health/db`
- `GET /version`
- `/docs` opens.
- `POST /auth/login` works.
- Admin UI login works at `/admin/login`.
- Admin dashboard opens.
- `/products` works.
- `/products/catalog` works.
- Removed legacy product endpoints return `404`:
  - `/products/search`
  - `/products/filter`
  - `/products/sort`
  - `/products/limited`
- Basic order flow works if safe test data is available.

Rollback and migration failure considerations:

- If a migration fails during startup, the app may not start.
- Check Render logs first to identify the failing migration or startup step.
- A code rollback may not automatically roll back database changes.
- If `SECRET_KEY` changes, existing JWTs and admin UI sessions become invalid.
- Do not weaken production `SECRET_KEY` enforcement.
- Do not skip the production audit.

Current CI covers SQLite Alembic upgrade, the data integrity audit, `python -m pytest`, and a focused PostgreSQL migration/audit job that uses a GitHub Actions PostgreSQL service container. The PostgreSQL CI job verifies `alembic upgrade head`, the data integrity audit script, and application import compatibility against the same database engine family used by Render production. A production audit against the real Render/production database is still required before deploy.

### Deployment Status

The deployed API was tested successfully on Render.

Verified production features:

- Health check endpoint
- Swagger documentation
- Admin registration and authorization
- Customer registration and authorization
- Admin self-registration prevention
- Customer cannot access admin-only routes
- Category creation by admin
- Product creation by admin
- Product catalog with filtering, sorting and pagination
- Customer profile creation
- Order creation by customer
- Product stock reduction after order creation
- Admin access to orders
- Order status update by admin
- PostgreSQL data persistence after redeploy


## How to Test in Swagger

Open the deployed Swagger documentation:

```text
https://online-shop-api-z9y4.onrender.com/docs
```

### 1. Create or update an admin user

Admin users are not created through public registration.

Use the admin seed script:

```bash
python seed_admin.py
```

The script uses these environment variables:

```env
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change_this_admin_password
```

On Render, these values are configured in the Web Service environment variables.

### 2. Authorize in Swagger

Click the **Authorize** button in Swagger.

Use:

```text
username: your ADMIN_USERNAME
password: your ADMIN_PASSWORD
```

Leave `client_id` and `client_secret` empty.

### 3. Test admin-only endpoints

After authorization, the admin user can create categories and products.

Example category endpoint:

```text
POST /categories
```

Example product endpoint:

```text
POST /products
```

### 4. Create a customer user

Use:

```text
POST /auth/register
```

Example request body:

```json
{
  "username": "customer_demo",
  "email": "customer_demo@example.com",
  "password": "123456"
}
```

Then authorize as `customer_demo`.

### 5. Create customer profile

Use:

```text
POST /customers
```

Example request body:

```json
{
  "name": "Demo Customer",
  "email": "customer_demo@example.com",
  "phone": "+380501112233"
}
```

### 6. Test product catalog

Use:

```text
GET /products/catalog
```

Example query:

```text
GET /products/catalog?skip=0&limit=10&sort_by=id&sort_order=asc
```

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite for local development
- PostgreSQL for production deployment on Render
- Alembic
- Pytest
- HTTPX
- Uvicorn
- Docker and Docker Compose
- GitHub Actions

## Features

- Product management
- Category management
- Customer management
- Order management
- Order items
- Product stock control
- Order total price calculation
- Order status validation
- Stock reduction after order creation
- Stock return after order cancellation
- Shop statistics endpoint
- Automated API tests
- Separate test database

## Project Structure

```text
online_shop/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── README.md
├── routes/
│   ├── __init__.py
│   ├── categories.py
│   ├── products.py
│   ├── customers.py
│   ├── orders.py
│   └── stats.py
└── tests/
    ├── conftest.py
    ├── helpers.py
    ├── test_auth.py
    ├── test_admin_ui.py
    ├── test_categories.py
    ├── test_products.py
    ├── test_customers.py
    ├── test_orders.py
    ├── test_stats.py
    ├── test_smoke.py
    ├── test_startup_scripts.py
    ├── test_audit_data_integrity.py
    ├── test_categories_integrity.py
    ├── test_customer_user_fk_integrity.py
    ├── test_orders_integrity.py
    ├── test_products_integrity.py
    └── test_users_integrity.py
```

## Installation

Follow these steps to install and run the project locally.

Clone the repository:

```bash

git clone https://github.com/Pavlo-Stelmakh/online_shop.git

cd online_shop

```
Create a virtual environment:

```bash

python -m venv .venv

```

Activate the virtual environment on macOS or Linux:

```bash

source .venv/bin/activate

```
Install dependencies:

```bash

pip install -r requirements.txt

```

## Environment Variables

The project uses environment variables for JWT authentication settings.

For local development only, the app can fall back to a development
`SECRET_KEY` if the variable is not set. In production or Render
environments, `SECRET_KEY` is required and must not use the default fallback
value. Do not commit or document real secret values.

Create a `.env` file in the project root:

```env
SECRET_KEY=your_real_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```
Example values are provided in:


```text
.env.example
```
The .env file is ignored by Git and must not be committed to GitHub.

Required environment variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Secret key used to sign JWT access tokens and admin UI session cookies. Required in production/Render; local fallback is only for development. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token expiration time in minutes |
| `DATABASE_URL` | PostgreSQL connection URL for production/Render. If absent, the app falls back to local SQLite, which is only for local development. |


## Admin Seed Script

Public registration always creates users with the `customer` role.

Admin users are created separately using the seed script:

```bash
python seed_admin.py
```

The script reads admin credentials from environment variables:

| Variable | Description |
|---|---|
| `ADMIN_USERNAME` | Admin username |
| `ADMIN_EMAIL` | Admin email |
| `ADMIN_PASSWORD` | Admin password |

Example `.env` values:

```env
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change_this_admin_password
```

If the admin user does not exist, the script creates it.  
If the admin user already exists, the script updates the email, password and role.


## Run the Project


Start the local development server:

```bash
uvicorn main:app --reload
```

Open the API documentation in your browser:

```text
http://127.0.0.1:8000/docs
```

Alternative documentation page:

```text
http://127.0.0.1:8000/redoc
```

## Run with Docker

The project can also be run with Docker.

Before running the project with Docker, create a `.env` file in the project root.

You can use `.env.example` as a template:

```env
SECRET_KEY=your_real_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Build and start the container:

```bash
docker compose up --build
```

Open the API documentation:

```text
http://127.0.0.1:8000/docs
```

Stop the container:

```bash
docker compose down
```

## Database Migrations

This project uses Alembic for database migrations.

Alembic allows changing the database structure without deleting the existing database file.

### Create a New Migration

After changing SQLAlchemy models in `models.py`, create a new migration:

```bash
alembic revision --autogenerate -m "describe your changes"
```

Example:

```bash
alembic revision --autogenerate -m "add product stock"
```

### Database / Migrations

- Alembic is used for database schema management and migrations.
- The application does not create tables with `Base.metadata.create_all()` at startup.
- Apply schema changes with `alembic upgrade head` before starting the app in production; `scripts/start.sh` does this automatically on Render.

### Apply Migrations

Apply all pending migrations:

```bash
alembic upgrade head
```

This updates the database structure to the latest version.

### Migration Files

Migration files are stored in:

```text
alembic/versions/
```

Each migration file describes changes to the database structure.

### Important Notes

Do not delete `shop.db` when changing models.

Use Alembic migrations instead.

Typical workflow:

```text
1. Change models.py
2. Create migration
3. Review migration file
4. Apply migration
5. Run tests
6. Commit changes
```

Commands:

```bash
alembic revision --autogenerate -m "migration message"
alembic upgrade head
python -m pytest
```

## API Endpoints

### Home

```text
GET /
```
Returns a simple response confirming that the API is running and provides quick links to documentation and health check.

Response:

```json
{
  "message": "Online Shop API is running",
  "docs": "/docs",
  "health": "/health"
}
```

### Health Check

The project includes a health check endpoint that can be used for deployment checks and monitoring.

```text
GET /health
```
Response:

```json
{
  "status": "ok"
}
```

### Database Health Check

Checks database connectivity with a lightweight query. The response intentionally does not expose `DATABASE_URL`, passwords, tokens, stack traces, or other secrets.

```text
GET /health/db
```
Successful response:

```json
{
  "status": "ok",
  "database": "ok"
}
```
Unavailable database response:

```json
{
  "status": "error",
  "database": "unavailable"
}
```

### Version

Returns safe deployment metadata from environment variables without making runtime git calls. Missing values fall back to `"unknown"`, and secrets are not included in the response.

```text
GET /version
```
Response:

```json
{
  "app": "online_shop",
  "version": "unknown",
  "commit": "unknown",
  "environment": "unknown"
}
```

Version metadata can be provided with `APP_VERSION`; commit metadata can be provided with `RENDER_GIT_COMMIT` or `COMMIT_SHA`; environment metadata can be provided with `APP_ENV`, `ENVIRONMENT`, or `RENDER_ENVIRONMENT`.

### Categories

```text
POST /categories
GET /categories
GET /categories/{category_id}/products
PUT /categories/{category_id}
DELETE /categories/{category_id}
```

Categories are used to group products.

Example category:

```json
{
  "name": "Laptops"
}
```
#### Category Update Validation

`PUT /categories/{category_id}` allows admin users to update category names.

Validation rules:

```text
name must not be empty
category_id must exist
category name must be unique
```

Successful update returns `200 OK`.

```json
{
  "id": 1,
  "name": "Updated Production Category"
}
```

If category does not exist, the endpoint returns `404 Not Found`.

```json
{
  "detail": "Category not found"
}
```

If category name already exists, the endpoint returns `400 Bad Request`.

```json
{
  "detail": "Category already exists"
}
```

Empty category name returns `422 Unprocessable Entity`.


#### Category Delete Protection

`DELETE /categories/{category_id}` allows admin users to delete empty categories.

Delete rules:

```text
admin users can delete empty categories
unauthenticated users cannot delete categories
customer users cannot delete categories
category_id must exist
categories with products cannot be deleted
```

Successful delete returns `200 OK`.

```json
{
  "message": "Category deleted successfully"
}
```

If category does not exist, the endpoint returns `404 Not Found`.

```json
{
  "detail": "Category not found"
}
```

If category has products, the endpoint returns `400 Bad Request`.

```json
{
  "detail": "Cannot delete category with products"
}
```


### Products

```text
GET /products
GET /products?skip=0&limit=10
GET /products?category_id=1
GET /products?min_price=100&max_price=500
GET /products?in_stock=true
GET /products
GET /products?sort_order=asc
GET /products?sort_by=price&sort_order=asc
GET /products?category_id=1&min_price=100&max_price=500&in_stock=true&sort_by=price&sort_order=asc&skip=0&limit=10
POST /products
GET /products/{product_id}
PUT /products/{product_id}
DELETE /products/{product_id}
GET /products/low-stock?threshold=5
GET /products/catalog
GET /products/catalog?search=Product
GET /products/catalog?search=Product&in_stock=true
GET /products/catalog?category_id=1&min_price=100&max_price=500&in_stock=true&sort_by=price&sort_order=asc&skip=0&limit=10
GET /products/catalog/pages
```

Products include name, price, exact `price_amount`, description, optional image URL, stock, low-stock threshold and category. Product create/update requests trim accepted name and description values, require name and description to be non-blank, and require `category_id` to be positive. Invalid product request schema inputs return FastAPI `422 Unprocessable Entity` responses with validation details.

Example product:

```json
{
  "name": "MacBook Air",
  "price": 1200,
  "description": "Apple laptop",
  "image_url": "https://example.com/macbook-air.jpg",
  "stock": 5,
  "category_id": 1
}
```


#### Low stock products

```text
GET /products/low-stock?threshold=5
```

Returns products where stock is less than or equal to the provided threshold.

This endpoint is available only for admin users.

Note: the admin UI uses each product's `low_stock_threshold` for dashboard
counts, product table styling and the `/admin/low-stock` page. The
`/products/low-stock` API endpoint remains backward-compatible and uses the
caller-supplied `threshold` query parameter.


### Product Pagination

The products list supports pagination using query parameters:

| Parameter | Description | Default |
|---|---|---:|
| `skip` | Number of products to skip | `0` |
| `limit` | Maximum number of products to return | `10` |

Example:

```text
GET /products?skip=0&limit=10
```

`GET /products` returns pagination metadata and wraps products in `items`:

```json
{
  "items": [
    {
      "id": 42,
      "name": "Wireless Mouse",
      "price": 199.99,
      "price_amount": "199.99",
      "description": "Ergonomic wireless mouse",
      "image_url": null,
      "stock": 12,
      "low_stock_threshold": 5,
      "category_id": 1,
      "category": {
        "id": 1,
        "name": "Electronics"
      }
    }
  ],
  "total": 125,
  "skip": 0,
  "limit": 10,
  "sort_by": "id",
  "sort_order": "desc"
}
```

`total` is the number of matching products before `skip` and `limit` are applied.


### Product Query Parameter Validation

Product list endpoints validate query parameters.

Validation rules:

| Parameter | Rule |
|---|---|
| `skip` | Must be greater than or equal to `0` |
| `limit` | Must be between `1` and `100` |
| `min_price` | Must be greater than or equal to `0` |
| `max_price` | Must be greater than or equal to `0` |

These rules apply to:

```text
GET /products
GET /products/catalog
```

Invalid query parameters return:

```json
{
  "detail": [
    {
      "type": "...",
      "loc": ["query", "limit"],
      "msg": "...",
      "input": "..."
    }
  ]
}
```


### Product Filtering

The products list supports filtering by category and price range.

Available query parameters:

| Parameter | Description | Example |
|---|---|---|
| `category_id` | Filter products by category ID | `category_id=1` |
| `min_price` | Minimum product price | `min_price=100` |
| `max_price` | Maximum product price | `max_price=500` |
| `in_stock` | Return only products with stock greater than 0 | `in_stock=true` |

Examples:

```text
GET /products?category_id=1
GET /products?min_price=100&max_price=500
GET /products?in_stock=true
GET /products?category_id=1&min_price=100&max_price=500&in_stock=true&skip=0&limit=10
```

### Product Sorting

The products list supports sorting by selected fields.

Available query parameters:

| Parameter | Description | Allowed values | Default |
|---|---|---|---|
| `sort_by` | Field used for sorting | `id`, `name`, `price`, `stock` | `id` |
| `sort_order` | Sorting direction | `asc`, `desc` | `desc` |

Examples:

```text
GET /products
GET /products?sort_order=asc
GET /products?sort_by=price&sort_order=asc
GET /products?sort_by=price&sort_order=desc
GET /products?sort_by=name&sort_order=asc
GET /products?sort_by=stock&sort_order=desc
GET /products?category_id=1&min_price=100&max_price=500&in_stock=true&sort_by=price&sort_order=asc&skip=0&limit=10
```

Invalid sorting fields return an error:

```json
{
  "detail": "Invalid sort_by value"
}
```

Invalid sorting order values return an error:

```json
{
  "detail": "Invalid sort_order value"
}
```


### Product Catalog Response

The project provides an extended product catalog endpoint:

```text
GET /products/catalog
```

`GET /products/catalog` follows the same offset pagination envelope style as `GET /products` and returns product items with metadata (`total`, `skip`, `limit`, `items`). It also supports catalog search.

For clients that need page-based pagination metadata, use:

```text
GET /products/catalog/pages
```

`GET /products/catalog/pages` returns page pagination metadata with `items`, `total`, `page`, `limit` and `pages` instead of the offset response's `skip`.

Response example:

```json
{
  "total": 25,
  "skip": 0,
  "limit": 10,
  "items": [
    {
      "id": 1,
      "name": "MacBook Air",
      "price": 1200,
      "price_amount": "1200.00",
      "description": "Apple laptop",
      "image_url": "https://example.com/macbook-air.jpg",
      "stock": 5,
      "low_stock_threshold": 5,
      "category_id": 1,
      "category": {
        "id": 1,
        "name": "Laptops"
      }
    }
  ]
}
```

The catalog endpoint supports product list filters plus catalog text search. `search` trims the supplied value, matches product name or description case-insensitively, can be combined with the other catalog filters, and rejects blank input.

| Parameter | Description |
|---|---|
| `skip` | Number of products to skip |
| `limit` | Maximum number of products to return |
| `category_id` | Filter products by category ID |
| `min_price` | Minimum product price |
| `max_price` | Maximum product price |
| `in_stock` | Return only products with stock greater than 0 |
| `sort_by` | Sort field: `id`, `name`, `price`, `stock` |
| `sort_order` | Sort direction: `asc`, `desc` |
| `search` | Case-insensitive text search across product name and description; blank search values return `400 Bad Request` |

Example:

```text
GET /products/catalog?category_id=1&min_price=100&max_price=500&in_stock=true&sort_by=price&sort_order=asc&skip=0&limit=10
```

Page-based catalog example:

```text
GET /products/catalog/pages?page=1&limit=10
```

Page-based response shape:

```json
{
  "items": [],
  "total": 25,
  "page": 1,
  "limit": 10,
  "pages": 3
}
```

#### Removed Legacy Product Endpoints

Breaking change: the legacy product convenience endpoints have been removed and now return `404 Not Found`:

```text
GET /products/search
GET /products/filter
GET /products/sort
GET /products/limited
```

Use the current product endpoints instead:

| Removed endpoint | Replacement |
|---|---|
| `GET /products/search` | `GET /products/catalog?search=...` |
| `GET /products/filter` | `GET /products?min_price=...&max_price=...` or `GET /products/catalog` |
| `GET /products/sort` | `GET /products?sort_by=price&sort_order=...` |
| `GET /products/limited` | `GET /products?limit=...` or `GET /products/catalog?limit=...` |

For current clients, prefer these supported product endpoints:

| Use case | Recommended endpoint |
|---|---|
| Simple product list, filtering, sorting, or offset metadata (`total`, `skip`, `limit`, `items`) | `GET /products` |
| Catalog product list with offset metadata (`total`, `skip`, `limit`, `items`) | `GET /products/catalog` |
| Product list with page metadata (`total`, `page`, `limit`, `pages`, `items`) | `GET /products/catalog/pages` |

#### Product Catalog Search

```text
GET /products/catalog?search=Product
GET /products/catalog?search=Product&in_stock=true
```

`GET /products/catalog` supports text search by product name and description. The `search` value is trimmed before matching, blank search values return `400 Bad Request`, and matches are case-insensitive substring matches against product names or descriptions.

Search can be combined with existing catalog filters:

```text
category_id
min_price
max_price
in_stock
sort_by
sort_order
skip
limit
```

The response keeps the catalog metadata format:

```json
{
  "total": 1,
  "skip": 0,
  "limit": 10,
  "items": []
}
```

#### Product Catalog Empty Search Validation

`GET /products/catalog` validates search input.

Validation rule:

```text
search cannot be empty or blank
```

Example invalid request:

```text
GET /products/catalog?search=%20%20%20
```

Invalid search value returns `400 Bad Request`.

```json
{
  "detail": "search cannot be empty"
}
```


#### Product Catalog Sort Validation

`GET /products/catalog` supports validated sorting.

Allowed `sort_by` values:

```text
id
name
price
stock
```

Allowed `sort_order` values:

```text
asc
desc
```

Examples:

```text
GET /products/catalog?sort_by=price&sort_order=asc
GET /products/catalog?sort_by=price&sort_order=desc
```

Invalid sorting parameters return `400 Bad Request`.

```json
{
  "detail": "Invalid sort_by value"
}
```

```json
{
  "detail": "Invalid sort_order value"
}
```

#### Product Catalog Price Range Validation

`GET /products/catalog` validates price range filters.

Validation rule:

```text
min_price cannot be greater than max_price
```

Example invalid request:

```text
GET /products/catalog?min_price=500&max_price=100
```

Invalid price range returns `400 Bad Request`.

```json
{
  "detail": "min_price cannot be greater than max_price"
}
```


### Customers

```text
POST /customers
GET /customers
GET /customers/{customer_id}
PUT /customers/{customer_id}
DELETE /customers/{customer_id}
GET /customers/{customer_id}/orders
```

Customers are linked to orders.

Access rules for customer endpoints:

| Method | Endpoint | Access |
|---|---|---|
| GET | `/customers/{customer_id}` | Owner or admin |
| PUT | `/customers/{customer_id}` | Owner or admin |
| DELETE | `/customers/{customer_id}` | Admin only |
| GET | `/customers/{customer_id}/orders` | Admin only |

Example customer:

```json
{
  "name": "John Smith",
  "email": "john@example.com",
  "phone": "+380501112233"
}
```

### Orders

```text
POST /orders
GET /orders
GET /orders?skip=0&limit=10
GET /orders?status=new
GET /orders?customer_id=2
GET /orders?status=new&customer_id=2
GET /orders?date_from=2026-06-01
GET /orders?date_to=2026-06-30
GET /orders?status=new&customer_id=2&date_from=2026-06-01&date_to=2026-06-30
GET /orders/my
GET /orders/{order_id}
PUT /orders/{order_id}/status
DELETE /orders/{order_id}
GET /orders/by-status
```

#### Order Status Filtering

`GET /orders/by-status` and `GET /orders` status filters are admin-only.

```text
GET /orders?status=new
GET /orders?status=paid
GET /orders?status=shipped
GET /orders?status=cancelled
```

Admin users can filter orders by status. The allowed order status contract is shared by the database, API validation, response schemas, and admin UI:

```text
new
paid
shipped
cancelled
```

Invalid `GET /orders?status=...` values return `400 Bad Request`:

```json
{
  "detail": "Invalid order status"
}
```

Invalid enum-constrained status values for `GET /orders/by-status` and `PUT /orders/{order_id}/status` return `422 Unprocessable Entity`.

Invalid admin UI order filters such as `/admin/orders?status=invalid` return a controlled `400 Bad Request` page with an invalid status filter message instead of silently showing an arbitrary empty filter result.

#### Order Customer Filtering

```text
GET /orders?customer_id=2
GET /orders?status=new&customer_id=2
```

Admin users can filter orders by customer ID.

This filter can be combined with order status filtering.

Examples:

```text
GET /orders?customer_id=2
GET /orders?status=new&customer_id=2
```

#### Order Date Filtering

```text
GET /orders?date_from=2026-06-01
GET /orders?date_to=2026-06-30
GET /orders?date_from=2026-06-01&date_to=2026-06-30
GET /orders?status=new&customer_id=2&date_from=2026-06-01&date_to=2026-06-30
```

Admin users can filter orders by creation date.

Date filters can be combined with status and customer filters.

Date format:

```text
YYYY-MM-DD
```

Invalid date format returns validation error `422`.


#### Order Pagination

```text
GET /orders?skip=0&limit=10
```

Admin users can paginate the orders list.

Pagination parameters:

| Parameter | Description |
|---|---|
| `skip` | Number of orders to skip |
| `limit` | Maximum number of orders to return |

Validation rules:

```text
skip >= 0
1 <= limit <= 100
```
Orders are returned newest first.

#### Orders Metadata Response

```json
{
  "total": 25,
  "skip": 0,
  "limit": 10,
  "items": []
}
```

The admin `GET /orders` endpoint returns pagination metadata.

Response fields:

| Field | Description |
|---|---|
| `total` | Total number of orders matching filters |
| `skip` | Number of skipped orders |
| `limit` | Maximum number of returned orders |
| `items` | List of returned orders |

#### Order Items Validation

`POST /orders` validates order items before creating an order. Basic request schema validation requires a non-empty `items` list and rejects non-positive `customer_id`, `product_id`, and `quantity` values with `422 Unprocessable Entity`. Duplicate products remain business validation and return `400 Bad Request`.

Validation rules:

```text
items must not be empty
customer_id must be greater than or equal to 1
product_id must be greater than or equal to 1
quantity must be greater than 0
product_id must exist
product_id must not be duplicated in the same order
product stock must be greater than or equal to quantity
```

Validation errors:

```json
{
  "detail": [
    {
      "type": "too_short",
      "loc": ["body", "items"],
      "msg": "List should have at least 1 item after validation, not 0"
    }
  ]
}
```

```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "items", 0, "quantity"],
      "msg": "Input should be greater than 0"
    }
  ]
}
```

```json
{
  "detail": "Duplicate product in order items"
}
```

```json
{
  "detail": "Product with id 999999 not found"
}
```

```json
{
  "detail": "Not enough stock for product Product Name"
}
```


#### Order Transaction Safety

`POST /orders` creates multi-item orders as a single consistent operation.

Transaction safety rules:

```text
invalid multi-item orders do not reduce stock
invalid multi-item orders do not create orders
valid multi-item orders calculate total_price correctly
valid multi-item orders reduce stock for all products
```

If one item in a multi-item order is invalid, the whole order is rejected.

Example invalid multi-item order:

```json
{
  "customer_id": 5,
  "items": [
    {
      "product_id": 1,
      "quantity": 1
    },
    {
      "product_id": 999999,
      "quantity": 1
    }
  ]
}
```

Expected result:

```json
{
  "detail": "Product with id 999999 not found"
}
```

In this case, no order is created and product stock is not reduced.

#### Customer Order History

```text
GET /orders/my
```

Returns orders that belong to the currently authenticated customer.

This endpoint requires customer authentication and returns only the current user's own orders.



#### Single Order Access Rules

```text
GET /orders/{order_id}
```

Access rules:

| User | Access |
|---|---|
| Admin | Can view any order |
| Customer | Can view only own orders |
| Not authenticated | Cannot access |

If a customer tries to access another customer's order, the API returns:

```json
{
  "detail": "Access denied"
}
```

Orders contain one or more order items.

Example order:

```json
{
  "customer_id": 1,
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    }
  ]
}
```


### Statistics

```text
GET /stats/summary
```

Returns basic shop statistics. This endpoint is admin-only.

Example response:

```json
{
  "products_count": 10,
  "customers_count": 3,
  "orders_count": 5,
  "total_revenue": 2400,
  "total_revenue_amount": "2400.00"
}
```

### Money response fields

Legacy money response fields (`price`, `unit_price`, `total_price`, and `total_revenue`) remain JSON numbers for backward compatibility. New companion `*_amount` fields (`price_amount`, `unit_price_amount`, `total_price_amount`, and `total_revenue_amount`) return exact decimal strings with exactly two decimal places. New API clients should prefer the `*_amount` fields for displaying or comparing money values.




## Authentication and Roles

The project includes JWT-based authentication and role-based access control.

### Authentication Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a new user with the `customer` role |
| POST | `/auth/login` | Login and receive a JWT `access_token` |
| GET | `/auth/me` | Get current authenticated user |

### User Roles

The project supports two user roles:

| Role | Description |
|---|---|
| `admin` | Can manage protected catalog, customer, order and statistics endpoints |
| `customer` | Can create and view their own customer profile and orders |

### Register Users

Public registration creates only `customer` users, even if a client sends a role-like field. Admin users are not created through `/auth/register`; use `seed_admin.py` with admin environment variables instead.

If the user is not authenticated, the API returns:

```json
{
  "detail": "Not authenticated"
}
```
If the user is authenticated but does not have the admin role, the API returns:

```json
{
  "detail": "Admin access required"
}
```

### Admin-Only Routes

The following routes require an authenticated user with the `admin` role:

| Method | Endpoint | Description |
|---|---|---|
| POST | `/categories` | Create category |
| POST | `/products` | Create product |
| PUT | `/products/{product_id}` | Update product |
| DELETE | `/products/{product_id}` | Delete product |
| GET | `/orders` | Get all orders |
| GET | `/orders/by-status` | Get orders by status |
| PUT | `/orders/{order_id}/status` | Update order status |
| DELETE | `/orders/{order_id}` | Delete order |
| GET | `/stats/summary` | Get shop statistics summary |
| DELETE | `/customers/{customer_id}` | Delete customer |
| GET | `/customers/{customer_id}/orders` | Get a customer's orders |


## Roles and Permissions Summary

The project uses role-based access control for protected API endpoints.

| Action | Admin | Customer | Not Authenticated |
|---|---:|---:|---:|
| View categories | Yes | Yes | Yes |
| Create category | Yes | No | No |
| View products | Yes | Yes | Yes |
| Create product | Yes | No | No |
| Update product | Yes | No | No |
| Delete product | Yes | No | No |
| Create own customer profile | Yes | Yes | No |
| View own customer profile `/customers/me` | Yes | Yes | No |
| Create order for own customer profile | Yes | Yes | No |
| Create order for another customer profile | Yes | No | No |
| View all orders | Yes | No | No |
| View single order | Yes | Own orders only | No |
| Update order status | Yes | No | No |
| Delete order | Yes | No | No |
| View own profile `/auth/me` | Yes | Yes | No |



### Access Rules

Public routes can be used without authentication.

Protected routes require a valid JWT access token.

Admin-only routes require both:

```text
valid JWT token
role = admin
```

If the user is not authenticated, the API returns:


```text
{
  "detail": "Not authenticated"
}
```

If the user is authenticated but does not have the admin role, the API returns:


```text
{
  "detail": "Admin access required"
}
```

## Customer Ownership Logic

The project links application users to customer profiles.

There are two related entities:

| Entity | Purpose |
|---|---|
| `User` | Used for authentication, JWT tokens, and roles |
| `Customer` | Used as a shop customer profile for orders |

Each customer profile is connected to a user through:

```text
customers.user_id
```

### Customer Profile

Authenticated users can create their own customer profile.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/customers` | Create customer profile for current authenticated user |
| GET | `/customers/me` | Get current user's customer profile |
| PUT | `/customers/me` | Update current user's customer profile without knowing `customer_id` |

`PUT /customers/me` uses the same customer profile request schema as profile creation. The `name`, `email`, and `phone` values are trimmed before saving; blank or whitespace-only values return `422`, and invalid email values return `422`.


If the authenticated user does not have a customer profile, the API returns:

```text
{
  "detail": "Customer profile not found"
}
```


### Order Ownership Rule
A customer can create orders only for their own customer profile.

For example, if customer_1 is authenticated, they cannot create an order using the customer_id of customer_2.

If a customer tries to create an order for another customer profile, the API returns:


```text
{
  "detail": "Customer profile not found"
}
```

### Admin Exception

Users with the admin role can manage orders and customer data according to admin-only permissions.

This means:

| Action | Admin | Customer |
|---|---:|---:|
| Create order for own customer profile | Yes | Yes |
| Create order for another customer profile | Yes | No |
| View all orders | Yes | No |
| Update order status | Yes | No |
| Delete order | Yes | No |


## Order Status Rules

Allowed order statuses:

```text
new
paid
shipped
cancelled
```

Allowed status transitions:

```text
new → paid
new → cancelled

paid → shipped
paid → cancelled

shipped → final status
cancelled → final status
```

Invalid status transitions are rejected by the API and by the admin order detail UI. The admin UI delegates status changes to the same order status service used by `PUT /orders/{order_id}/status`, including stock restoration when an order is cancelled.

Examples of invalid transitions:

```text
new → shipped
paid → new
shipped → cancelled
cancelled → paid
```

## Customer Ownership Logic

The project links application users to customer profiles.

There are two related entities:

| Entity | Purpose |
|---|---|
| `User` | Used for authentication, JWT tokens, and roles |
| `Customer` | Used as a shop customer profile for orders |

Each customer profile is connected to a user through:

```text
customers.user_id
```

## Stock Logic

Each product has a stock value.

The stock value shows how many units of the product are available.

Example product:

```json
{
  "name": "MacBook Air",
  "price": 1200,
  "description": "Apple laptop",
  "stock": 5,
  "category_id": 1
}
```

When an order is created, product stock is reduced.

Example:

```text
Product stock before order: 5
Ordered quantity: 2
Product stock after order: 3
```

If an order is cancelled, product stock is returned.

Example:

```text
Product stock before cancellation: 3
Cancelled order quantity: 2
Product stock after cancellation: 5
```

If the requested quantity is greater than the available stock, the API returns an error.

Example:

```json
{
  "detail": "Not enough stock for product MacBook Air"
}
```

## Validation Rules

The API validates important business rules to prevent incorrect data.

### Categories

Category names must be unique.

If a category with the same name already exists, the API returns an error.

Example error:

```json
{
  "detail": "Category already exists"
}
```

### Customers

Customer emails must be unique.

If a customer with the same email already exists, the API returns an error.

Example error:

```json
{
  "detail": "Customer with this email already exists"
}
```

Customer, authentication and category request schemas use stricter validation and return `422 Unprocessable Entity` for invalid schema input.

### Products

Product names and descriptions are trimmed and must be non-blank. Product `category_id` must be positive, product stock cannot be negative, and invalid product request schema inputs return `422 Unprocessable Entity`.

Example invalid product:

```json
{
  "name": "MacBook Air",
  "price": 1200,
  "description": "Apple laptop",
  "stock": -1,
  "category_id": 1
}
```

The API rejects this request because stock must be greater than or equal to 0.

### Orders

Order quantity must be at least 1.

Example invalid order item:

```json
{
  "product_id": 1,
  "quantity": 0
}
```

The order items list cannot be empty.

Example invalid order:

```json
{
  "customer_id": 1,
  "items": []
}
```

The API rejects this request with `422 Unprocessable Entity` because an order must contain at least one product. Duplicate products are still handled as business validation with `400 Bad Request`.

### Order Status

Order status must be one of the allowed values:

```text
new
paid
shipped
cancelled
```

Invalid status values are rejected.

Example invalid status:

```text
test
```

Invalid status transitions are also rejected.

Example:

```text
shipped → cancelled
```

This transition is not allowed because `shipped` is a final status.


## Run Tests

The project includes automated API tests.

Tests check the main business logic of the application:

```text
home and health endpoints
authentication and JWT login
secure public registration
role-based access control
category creation
product creation
product filtering, sorting and pagination
customer profile creation
customer ownership logic
order creation
stock reduction after order creation
stock return after order cancellation
order status validation
admin-only route protection
```
Run tests:

```bash
python -m pytest
```
Expected result:

```text
379 passed
```
Current test suite includes 379 automated tests covering authentication, roles, products, categories, customers, orders, stock logic, order status rules, deployment endpoints, admin UI authentication, security behavior, startup scripts, and data integrity checks.

The tests use a separate SQLite database:

```text
test_shop.db
```
Local development uses SQLite by default:

```text
shop.db
```
Production deployment uses PostgreSQL through the DATABASE_URL environment variable.

Database files are ignored by Git.

This means tests do not affect the local development database or the production PostgreSQL database.

## Git Ignore

The project uses `.gitignore` to exclude local, temporary and technical files from Git.

Ignored files and folders:

```text
.venv/
venv/
__pycache__/
*.py[cod]
*.db
*.sqlite3
.pytest_cache/
.idea/
.DS_Store
```

### Why these files are ignored

Virtual environment files are ignored because dependencies can be installed again from `requirements.txt`.

```text
.venv/
venv/
```

Python cache files are ignored because they are generated automatically.

```text
__pycache__/
*.py[cod]
```

SQLite database files are ignored because they contain local application data and test data.

```text
*.db
*.sqlite3
```

Pytest cache is ignored because it is generated automatically when tests are run.

```text
.pytest_cache/
```

PyCharm project settings are ignored because they are local IDE settings.

```text
.idea/
```

macOS system files are ignored because they are not part of the project.

```text
.DS_Store
```

## Development Workflow

This project uses Git and GitHub for version control.

Typical development workflow:

```bash
git status
```

Check which files were changed.

```bash
git add .
```

Add all changed files to Git.

```bash
git commit -m "Your commit message"
```

Save changes locally with a clear commit message.

```bash
git push
```

Send changes to GitHub.

### Recommended workflow

Before making changes, check the current Git status:

```bash
git status
```

After changing code, run tests:

```bash
python -m pytest
```

If tests pass, save the changes:

```bash
git add .
git commit -m "Describe your changes"
git push
```

### Example commit messages

```text
Add customers API
Add orders API
Add product stock management
Add shop statistics endpoint
Add API tests
Update README
```

Use short and clear commit messages that explain what was changed.


## Current Project Status

The project is a deployed portfolio-ready backend API for an online shop.

Current production status:

```text
FastAPI application deployed on Render
Render PostgreSQL connected through DATABASE_URL
JWT authentication implemented
Public registration creates customer users only
Admin users are managed through seed_admin.py
Role-based access control implemented
Product catalog supports pagination, filtering and sorting
Order creation reduces product stock
Order cancellation returns product stock
Admin users can manage categories, products and orders
Customer users can create orders only for their own customer profile
Automated tests are configured with pytest
GitHub Actions CI workflow is configured
```


## Future Improvements

Possible next steps for improving the project:

```text
Add user authentication
Add admin and customer roles
Add password hashing
Add JWT-based login
Add Alembic database migrations
Add Docker support
Add GitHub Actions for automatic tests
Add product images
Add product availability status
Add customer order history
Add pagination for customers and orders
Add filtering orders by date
Add filtering orders by customer
Add detailed revenue statistics
Add frontend interface
Add error logging
Add environment variables
Add production database support
```

### Authentication

Add user registration and login.

Possible features:

```text
user registration
user login
password hashing
JWT access tokens
protected routes
```

### Roles

Add different access levels:

```text
admin
customer
```

Example:

```text
admin can create, edit and safely delete products
customer can create orders and view own orders
```

### Database Migrations

Add Alembic for database migrations.

This will allow changing database structure without deleting `shop.db`.

Example future migration:

```text
add new field to products
add new field to orders
change table structure safely
```

### Docker

Add Docker support to run the project in a container.

Possible files:

```text
Dockerfile
docker-compose.yml
```

### GitHub Actions

Add automatic testing on GitHub.

This means tests will run automatically after every push.

Example workflow:

```text
push code to GitHub
GitHub runs tests
if tests pass, code is safe
if tests fail, GitHub shows an error
```

### Frontend

Add a simple frontend interface.

Possible pages:

```text
products page
categories page
customers page
orders page
statistics page
```

### Product Images

Add product image support.

Possible fields:

```text
image_url
image_filename
```


#### Product Update Validation

`PUT /products/{product_id}` validates product data before updating a product.

Validation rules:

```text
name must not be empty
price must be greater than 0
stock must be greater than or equal to 0
category_id must exist
```

Validation errors:

```text
422 Unprocessable Entity
```

```json
{
  "detail": "Category not found"
}
```



### Advanced Statistics

Add more detailed shop analytics.

Possible statistics:

```text
total revenue
paid orders count
cancelled orders count
best-selling products
low-stock products
revenue by period

```

## Version History

```text

v1.0.0 — base portfolio release
v1.1.0 — product image URL support
v1.2.0 — low stock endpoint
v1.3.0 — customer order history
v1.4.0 — protected single order access
v1.5.0 — order status filtering
v1.6.0 — admin order filtering by customer
v1.7.0 — order date filtering
v1.8.0 — order pagination
v1.9.0 — orders metadata response
v2.0.0 — order items validation and stock protection
v2.1.0 — order total consistency and transaction safety
v2.2.0 — order duplicate product validation
v2.3.0 — product update validation
v2.4.0 — product search endpoint
v2.5.0 — product catalog sort validation
v2.6.0 — product catalog price range validation
v2.7.0 — product catalog empty search validation
v2.8.0 — category update validation
v2.9.0 — category delete protection
v3.0.0 — portfolio polish
v3.1.0 — basic admin dashboard UI
v3.2.0 - admin products page
v3.3.0 — admin orders page
v3.3.0 — admin orders page
v3.4.0 — admin categories page
v3.5.0 — admin customers page
v3.6.0 — admin low stock page
v3.7.0 — admin dashboard navigation polish
v3.8.0 — admin order status badges
v3.9.0 — admin dashboard stats cards polish
v4.0.0 — admin dashboard UI final polish
v4.1.0 — clickable dashboard cards
v4.2.0 — admin orders filter UI
v4.3.0 — admin products search/filter UI
v4.4.0 — admin categories search UI
v4.5.0 — admin customers search UI
v4.6.0 — product-specific low stock threshold
v4.7.0 — admin dashboard login authentication
v4.8.0 — admin test cookie warnings cleanup
v4.9.0 — admin product create form
v5.0.0 — admin product update form
v5.1.0 — admin product delete action
```
## Project Status

The project is deployed and production-tested on Render.

Current status:

```text
Production-ready portfolio backend API
```
Main quality checks:

```text
379 automated tests passed
GitHub Actions CI enabled
Render deployment verified
Swagger UI available
Docker support included
```
## Future Improvements

Possible future improvements:

- Add product reviews and ratings
- Add cart functionality
- Add payment integration
- Add order invoices
- Add email notifications
- Add refresh tokens
- Add admin dashboard UI
- Add advanced analytics
- Add PostgreSQL-specific integration tests


## Demo data seed

Use `scripts/seed_demo_data.py` to safely clean noisy demo/test records and seed a polished portfolio catalog. The script is intended **only for demo databases**. It is not a general production cleanup tool.

Safety behavior:

- The script connects to the database from `DATABASE_URL`.
- It refuses to run unless `DEMO_MODE=true` is set or `--force-demo-reset` is passed.
- It removes only records that match demo/test markers such as Swagger, Render, validation or test data, plus the curated demo products it recreates.
- It deletes related demo data in dependency order: `order_items`, `orders`, `customers`, `products`, then empty demo/test `categories`.
- It does not delete admin users.

Seeded demo categories:

```text
Electronics
Accessories
Office
Home
```

Seeded demo products:

```text
Wireless Mouse
Mechanical Keyboard
USB-C Hub
Laptop Stand
Noise Cancelling Headphones
External SSD 1TB
Office Desk Lamp
Smart Plug
Monitor 27 inch
Backpack
```

### Run demo seed locally

Run migrations first, point `DATABASE_URL` at the local demo database, and enable demo mode explicitly:

```bash
export DATABASE_URL="sqlite:///./shop.db"
export DEMO_MODE=true
python scripts/seed_demo_data.py
```

Alternatively, use the explicit reset flag for one manual run:

```bash
DATABASE_URL="sqlite:///./shop.db" python scripts/seed_demo_data.py --force-demo-reset
```

### Run demo seed manually on Render

Run this only against the Render demo database, not against a real customer production database.

1. Open the Render service dashboard.
2. Go to the service shell or one-off job/manual command runner.
3. Confirm `DATABASE_URL` points to the intended demo database.
4. Run:

```bash
DEMO_MODE=true python scripts/seed_demo_data.py
```

If using a one-off manual command where environment variables are already configured on the service, the command can be:

```bash
python scripts/seed_demo_data.py --force-demo-reset
```

Review the printed deletion/creation counts after the command finishes.
