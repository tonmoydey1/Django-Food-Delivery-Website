# Tonmoy Eats Django Food Ordering Website

Tonmoy Eats is a complete Django food ordering website with restaurant browsing, categories, search and filters, AJAX cart, checkout, login/register, user profile, order history, live order tracking, email notifications, payment hooks, and invoice PDF generation.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Environment Variables

Secrets are not stored in the repository. Use `.env.example` as a reference and set values in PowerShell before running the server:

```powershell
$env:DJANGO_SECRET_KEY="change-me"
$env:STRIPE_SECRET_KEY="sk_test_..."
$env:STRIPE_PUBLISHABLE_KEY="pk_test_..."
$env:EMAIL_HOST_USER="your-email@gmail.com"
$env:EMAIL_HOST_PASSWORD="your-app-password"
```

## Payment

Cash on delivery works immediately. Card payment for orders falls back to demo mode without Stripe keys. Premium subscriptions require Stripe keys. To use Stripe Checkout, install requirements and set:

```powershell
$env:STRIPE_SECRET_KEY="sk_test_..."
$env:STRIPE_PUBLISHABLE_KEY="pk_test_..."
```

The webhook endpoint is `/stripe/webhook/`.

## Email

Development email uses Django's console email backend by default, so OTP and order emails print in the terminal. Set `EMAIL_BACKEND`, SMTP host, and credentials in environment variables for real email delivery.

## Main Modules

- Restaurant model, categories, and menu items
- Search, cuisine/category filters, open-now filter, sorting
- AJAX cart with quantity updates and one-restaurant cart rule
- Checkout with guest and logged-in order flow
- Cash on delivery and Stripe-ready card checkout
- Live tracking API polled by JavaScript
- Order history and detail pages
- User profile page with saved delivery details
- Email notifications for confirmations and status changes
- Invoice PDF endpoint
- Admin management for restaurants, menu, orders, payments, and profiles
