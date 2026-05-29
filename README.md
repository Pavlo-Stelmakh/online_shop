# Online Shop API

Backend API for a simple online shop built with FastAPI, SQLite, SQLAlchemy and Pytest.

The project demonstrates core backend functionality for an online store: products, categories, customers, orders, stock management, order status rules, statistics and automated API tests.

## Tech Stack

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- Pytest
- HTTPX
- Uvicorn

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
    └── test_main.py
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

Returns a simple message confirming that the API is running.

### Categories

```text
POST /categories
GET /categories
GET /categories/{category_id}/products
```

Categories are used to group products.

Example category:

```json
{
  "name": "Laptops"
}
```

### Products

```text
POST /products
GET /products
GET /products/{product_id}
PUT /products/{product_id}
DELETE /products/{product_id}
GET /products/search
GET /products/filter
GET /products/sort
GET /products/limited
GET /products/catalog
GET /products/catalog/pages
```

Products include name, price, description, stock and category.

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
GET /orders/{order_id}
PUT /orders/{order_id}/status
DELETE /orders/{order_id}
GET /orders/by-status
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

Returns basic shop statistics.

Example response:

```json
{
  "products_count": 10,
  "customers_count": 3,
  "orders_count": 5,
  "total_revenue": 2400
}
```
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

Invalid status transitions are rejected by the API.

Examples of invalid transitions:

```text
new → shipped
paid → new
shipped → cancelled
cancelled → paid
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

### Products

Product stock cannot be negative.

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

The API rejects this request because an order must contain at least one product.

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
home endpoint
category creation
product creation
customer creation
order creation
stock reduction after order creation
stock return after order cancellation
```

Run tests:

```bash
python -m pytest
```

Expected result:

```text
6 passed
```

The tests use a separate SQLite database:

```text
test_shop.db
```

The main application uses:

```text
shop.db
```

Both database files are ignored by Git.

This means tests do not affect the main application database.

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

Implemented features:

```text
FastAPI application structure
SQLite database connection
SQLAlchemy models
Pydantic schemas
Route-based project structure
Product API
Category API
Customer API
Order API
Order items
Product stock management
Order total price calculation
Order cancellation logic
Order status validation
Order status transition rules
Shop statistics endpoint
Automated API tests
Separate test database
Git and GitHub setup
README documentation
```

Current entities:

```text
Category
Product
Customer
Order
OrderItem
```

Current route files:

```text
routes/categories.py
routes/products.py
routes/customers.py
routes/orders.py
routes/stats.py
```

Current database files:

```text
shop.db       — main local application database
test_shop.db  — separate database for automated tests
```

Both database files are ignored by Git.

Current test coverage:

```text
home endpoint
category creation
product creation
customer creation
order creation
stock reduction after order creation
stock return after order cancellation
```

Current project status:

```text
The project is functional as a local backend API for a simple online shop.
It can be run locally, tested automatically and stored on GitHub.
```




## Future Improvements

Possible next steps:

- Add user authentication
- Add admin/user roles
- Add Alembic database migrations
- Add Docker support
- Add frontend interface
- Add pagination for customers and orders
- Add product images
- Add order history with detailed customer information
- Add CI testing with GitHub Actions


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
admin can create, update and delete products
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

### Production Improvements

Before using this project in production, add:

```text
proper authentication
secure configuration
environment variables
production database
logging
error monitoring
input sanitization
deployment setup
```
