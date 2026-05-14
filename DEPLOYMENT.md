# Tonmoy Eats Deployment Guide

This project is prepared for Render deployment with Django, Gunicorn, WhiteNoise static files, and Render PostgreSQL.

## What deploys

- Django web app through `gunicorn config.wsgi:application`
- PostgreSQL database through `render.yaml`
- Static CSS, JavaScript, and images through `collectstatic` + WhiteNoise
- Migrations through `python manage.py migrate --no-input`
- Starter restaurant/category/menu data through `python manage.py seed_data`
- Email OTP, order confirmation email, invoice attachment, and password reset email through SMTP
- Stripe Checkout for normal card orders and Premium subscriptions

## 1. Push the project to GitHub

Make sure `.env` is not committed. It is already ignored by `.gitignore`.

```powershell
git add .
git commit -m "Prepare Django app for Render deployment"
git push
```

## 2. Create the Render Blueprint

1. Open Render Dashboard.
2. Go to **Blueprints**.
3. Click **New Blueprint Instance**.
4. Connect the GitHub repository for this project.
5. Render will read `render.yaml` and create:
   - `tonmoy-eats`
   - `tonmoy-eats-db`

## 3. Add secret values when Render asks

Render prompts for the variables marked `sync: false`.

Use these values:

```text
EMAIL_HOST_USER=your Gmail address
EMAIL_HOST_PASSWORD=your Gmail app password
DEFAULT_FROM_EMAIL=Tonmoy Eats <your Gmail address>

STRIPE_PUBLISHABLE_KEY=pk_test_or_pk_live...
STRIPE_SECRET_KEY=sk_test_or_sk_live...
STRIPE_WEBHOOK_SECRET=whsec_...
```

For Gmail, use a Google App Password, not your normal Gmail password.

## 4. Set the deployed site URL

After Render gives you the live URL, add or update this environment variable:

```text
SITE_URL=https://your-render-service.onrender.com
```

If you add a custom domain, also update:

```text
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,.onrender.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://*.onrender.com
SITE_URL=https://yourdomain.com
```

## 5. Stripe webhook

In Stripe Dashboard, create a webhook endpoint:

```text
https://your-domain-or-render-url/stripe/webhook/
```

Select this event:

```text
checkout.session.completed
```

Copy the webhook signing secret and set:

```text
STRIPE_WEBHOOK_SECRET=whsec_...
```

Without the webhook, users can still complete checkout and return to the success page, but the webhook makes payment confirmation more reliable.

## 6. Create admin account

After the first deploy succeeds, open Render Shell and run:

```bash
python manage.py createsuperuser
```

Then login at:

```text
https://your-domain/admin/
```

## 7. Production test checklist

- Register a new account and confirm registration OTP email arrives.
- Login with password and confirm login OTP email arrives.
- Add item to cart and place a cash-on-delivery order.
- Place a Stripe card order with Stripe test card `4242 4242 4242 4242`.
- Confirm order email arrives with invoice PDF attached.
- Activate Weekly, Monthly, and Annual Premium from `/premium/`.
- Confirm Premium badge appears in the navbar after Stripe payment.
- Check `/orders/`, order details, invoice PDF, and live tracking.

## Important production note

Render free services can sleep and free databases have limitations. For a real public business website, use a paid web service/database plan and enable database backups.
