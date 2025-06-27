# MiEcommerce API (Django Backend)

This repository contains the REST API backend for the MiEcommerce application, built with Django and Django REST Framework. It provides endpoints for managing products, inventory, users, shopping carts, quotes, and more.

## Key Features

- **Product Management:** Full CRUD for products, categories, subcategories, tags, and images.
- **Inventory:** Stock control with entries and automatic deduction upon sale completion.
- **Authentication:** JWT (JSON Web Tokens) based user authentication system with email as the primary identifier.
- **Cart & Quotes:** Logic for shopping carts and quote generation.
- **Banners & Featured Products:** Endpoints to manage dynamic content for the frontend.
- **API Documentation:** OpenAPI schema generated with `drf-spectacular`.

## Tech Stack

- **Framework:** Django
- **API:** Django REST Framework
- **Database:** PostgreSQL
- **Authentication:** djangorestframework-simplejwt
- **API Documentation:** drf-spectacular
- **Application Server (Production):** Gunicorn
- **Deployment:** Docker & Docker Compose

## Local Environment Setup (with Docker)

This project is designed to run with Docker and Docker Compose to ensure a consistent development environment.

### Prerequisites

- Docker
- Docker Compose

### Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone [YOUR_REPOSITORY_URL]
    cd [repository-name]/backend
    ```

2.  **Configure Environment Variables:**
    Create a `.env` file in the directory where your `docker-compose.yml` is located (likely the monorepo root). This file will hold environment variables for all services.

    Copy the contents of `.env.example` (if it exists) or use the following template:
    ```env
    # .env (in the root directory)

    # Django
    DJANGO_SECRET_KEY=your_super_long_and_secure_key_here_change_it
    DJANGO_DEBUG=1
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
    
    # CORS/CSRF for local development (allows access from the React frontend)
    DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
    DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

    # PostgreSQL
    POSTGRES_DB=ecommercedb
    POSTGRES_USER=ecommerceuser
    POSTGRES_PASSWORD=averyhardpassword
    ```

3.  **Build and Run the Containers:**
    From the root directory where `docker-compose.yml` is located, run:
    ```bash
    docker-compose up --build -d
    ```

4.  **Run Migrations and Create a Superuser:**
    Once the containers are running, execute the following commands in a new terminal:

    *   **Apply migrations:**
        ```bash
        docker-compose exec backend python manage.py migrate
        ```
    *   **Create a superuser for the Django Admin:**
        ```bash
        docker-compose exec backend python manage.py createsuperuser
        ```

5.  **Seed the Database (Optional):**
    If you have a management command to populate the database with test data, run it:
    ```bash
    docker-compose exec backend python manage.py populate_data
    ```

### Accessing the Application

-   **API:** The API will be available at `http://localhost:8000/api/` (if port 8000 is mapped in `docker-compose.yml` for development) or through Nginx at `http://localhost/api/`.
-   **Django Admin:** `http://localhost:8000/admin/` or `http://localhost/admin/`.
-   **API Documentation (Swagger):** `http://localhost:8000/api/schema/swagger-ui/`
-   **API Documentation (ReDoc):** `http://localhost:8000/api/schema/redoc/`

## Running Tests

To run the automated tests for the backend, use the following command:
```bash
docker-compose exec backend pytest