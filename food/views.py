import json
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .cart import Cart, CartRestaurantMismatch
from .forms import CheckoutForm, ProfileForm, RegisterForm, UserUpdateForm
from .models import Category, MenuItem, Order, OrderItem, Payment, PremiumPayment, Restaurant
from .utils import (
    render_invoice_pdf,
    send_login_otp_email,
    send_order_confirmation_email,
    send_register_otp_email,
    tracking_payload,
)


PREMIUM_PLANS = {
    PremiumPayment.PLAN_WEEKLY: {
        'name': 'Weekly',
        'amount': Decimal('29.00'),
        'discount_percent': 5,
        'duration_days': 7,
        'interval': 'week',
        'duration_text': '7 days',
        'badge': 'Starter',
        'description': 'Try Premium for a week with free delivery and 5% food discounts.',
        'priority_support': False,
    },
    PremiumPayment.PLAN_MONTHLY: {
        'name': 'Monthly',
        'amount': Decimal('99.00'),
        'discount_percent': 20,
        'duration_days': 30,
        'interval': 'month',
        'duration_text': '30 days',
        'badge': 'Popular',
        'description': 'Best for regular orders with 20% food discounts, monthly offers, and priority support.',
        'priority_support': True,
        'featured': True,
    },
    PremiumPayment.PLAN_ANNUAL: {
        'name': 'Annual',
        'amount': Decimal('999.00'),
        'discount_percent': 25,
        'duration_days': 365,
        'interval': 'year',
        'duration_text': '1 year',
        'badge': 'Best value',
        'description': 'A full year of Premium benefits with 25% food discounts and the biggest long-term savings.',
        'priority_support': True,
    },
}


def home(request):
    categories = Category.objects.annotate(item_count=Count('menu_items')).filter(item_count__gt=0)[:8]
    restaurants = Restaurant.objects.filter(is_active=True).annotate(menu_count=Count('menu_items'))[:6]
    featured_items = (
        MenuItem.objects.select_related('restaurant', 'category')
        .filter(is_available=True, restaurant__is_active=True)
        .order_by('-is_featured', '-restaurant__rating')[:8]
    )
    context = {
        'categories': categories,
        'restaurants': restaurants,
        'featured_items': featured_items,
        'average_rating': restaurants.aggregate(avg=Avg('rating'))['avg'] or 0,
    }
    return render(request, 'food/home.html', context)


def restaurant_list(request):
    query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    category_slug = request.GET.get('category', '').strip()
    cuisine = request.GET.get('cuisine', '').strip()
    open_now = request.GET.get('open_now') == '1'
    sort = request.GET.get('sort', 'recommended')

    restaurants = Restaurant.objects.filter(is_active=True).annotate(menu_count=Count('menu_items'))
    if query:
        restaurants = restaurants.filter(
            Q(name__icontains=query)
            | Q(tagline__icontains=query)
            | Q(cuisine__icontains=query)
            | Q(menu_items__name__icontains=query)
            | Q(menu_items__description__icontains=query)
            | Q(menu_items__category__name__icontains=query)
        ).distinct()
    if location and location.lower() not in ['tezpur', 'current location']:
        restaurants = restaurants.filter(Q(city__icontains=location) | Q(address__icontains=location)).distinct()
    if category_slug:
        restaurants = restaurants.filter(menu_items__category__slug=category_slug).distinct()
    if cuisine:
        restaurants = restaurants.filter(cuisine__iexact=cuisine)
    if open_now:
        restaurants = [restaurant for restaurant in restaurants if restaurant.is_open_now]
    else:
        restaurants = list(restaurants)

    if sort == 'delivery':
        restaurants = sorted(restaurants, key=lambda restaurant: restaurant.delivery_time)
    elif sort == 'minimum':
        restaurants = sorted(restaurants, key=lambda restaurant: restaurant.minimum_order)
    elif sort == 'rating':
        restaurants = sorted(restaurants, key=lambda restaurant: restaurant.rating, reverse=True)
    else:
        restaurants = sorted(restaurants, key=lambda restaurant: (restaurant.is_featured, restaurant.rating), reverse=True)

    context = {
        'restaurants': restaurants,
        'categories': Category.objects.all(),
        'cuisines': Restaurant.objects.filter(is_active=True).values_list('cuisine', flat=True).distinct().order_by('cuisine'),
        'filters': {
            'q': query,
            'location': location,
            'category': category_slug,
            'cuisine': cuisine,
            'open_now': open_now,
            'sort': sort,
        },
    }
    return render(request, 'food/restaurant_list.html', context)


def restaurant_detail(request, slug):
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
    category_slug = request.GET.get('category', '').strip()
    query = request.GET.get('q', '').strip()
    menu_items = restaurant.menu_items.select_related('category').filter(is_available=True)

    if category_slug:
        menu_items = menu_items.filter(category__slug=category_slug)
    if query:
        menu_items = menu_items.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(labels__icontains=query))

    categories = Category.objects.filter(menu_items__restaurant=restaurant).distinct()
    context = {
        'restaurant': restaurant,
        'categories': categories,
        'menu_items': menu_items,
        'selected_category': category_slug,
        'query': query,
    }
    return render(request, 'food/restaurant_detail.html', context)


def cart_page(request):
    cart = Cart(request)
    return render(request, 'food/cart.html', {'cart': cart, 'cart_items': cart.items()})


@require_POST
def cart_add(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                'ok': False,
                'login_required': True,
                'message': 'Please login or create an account before adding food to your cart.',
                'login_url': reverse('login'),
                'register_url': reverse('register'),
            },
            status=401,
        )
    payload = request_payload(request)
    item = get_object_or_404(MenuItem, id=payload.get('item_id'), is_available=True, restaurant__is_active=True)
    quantity = payload.get('quantity', 1)
    replace = str(payload.get('replace', '')).lower() in ['1', 'true', 'yes']
    cart = Cart(request)
    try:
        cart.add(item, quantity=quantity, replace=replace)
    except CartRestaurantMismatch:
        current_restaurant = cart.restaurant.name if cart.restaurant else 'another restaurant'
        return JsonResponse(
            {
                'ok': False,
                'requires_confirmation': True,
                'message': f'Your cart has food from {current_restaurant}. Replace it with {item.restaurant.name}?',
            },
            status=409,
        )
    return JsonResponse({'ok': True, 'message': f'{item.name} added to cart.', 'cart': cart.as_dict()})


@require_POST
def cart_update(request):
    payload = request_payload(request)
    cart = Cart(request)
    cart.update(payload.get('item_id'), payload.get('quantity', 1))
    return JsonResponse({'ok': True, 'cart': cart.as_dict()})


@require_POST
def cart_remove(request):
    payload = request_payload(request)
    cart = Cart(request)
    cart.remove(payload.get('item_id'))
    return JsonResponse({'ok': True, 'cart': cart.as_dict()})


@require_POST
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    return JsonResponse({'ok': True, 'cart': cart.as_dict()})


def checkout(request):
    cart = Cart(request)
    if not cart.count:
        messages.info(request, 'Your cart is empty. Add a meal first.')
        return redirect('restaurant_list')

    initial = {}
    if request.user.is_authenticated:
        profile = request.user.profile
        initial = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': profile.phone,
            'address': profile.address,
            'city': profile.city,
            'postcode': profile.postcode,
            'delivery_notes': profile.delivery_notes,
        }

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    restaurant=cart.restaurant,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'],
                    address=form.cleaned_data['address'],
                    city=form.cleaned_data['city'],
                    postcode=form.cleaned_data['postcode'],
                    delivery_notes=form.cleaned_data['delivery_notes'],
                    payment_method=form.cleaned_data['payment_method'],
                    payment_status=Order.PAYMENT_PENDING,
                    subtotal=cart.subtotal,
                    delivery_fee=cart.delivery_fee,
                    tax=cart.tax,
                    discount=cart.discount,
                    total=cart.total,
                )
                for row in cart.items():
                    item = row['item']
                    OrderItem.objects.create(
                        order=order,
                        menu_item=item,
                        name=item.name,
                        price=item.price,
                        quantity=row['quantity'],
                        line_total=row['line_total'],
                    )
                if request.user.is_authenticated:
                    sync_profile_from_checkout(request.user, form.cleaned_data)
                cart.clear()

            if order.payment_method == Order.PAYMENT_CARD:
                return redirect('payment_start', tracking_code=order.tracking_code)

            Payment.objects.create(
                order=order,
                provider='cash-on-delivery',
                amount=order.total,
                status=Order.PAYMENT_PENDING,
            )
            if not send_order_confirmation_email(order, request):
                messages.warning(request, 'Order placed, but the confirmation email could not be sent. Check SMTP settings.')
            messages.success(request, f'Order {order.tracking_code} placed successfully.')
            return redirect(order.get_absolute_url())
    else:
        form = CheckoutForm(initial=initial)

    return render(request, 'food/checkout.html', {'form': form, 'cart': cart, 'cart_items': cart.items()})


def payment_start(request, tracking_code):
    order = get_object_or_404(Order, tracking_code=tracking_code)
    if order.payment_method != Order.PAYMENT_CARD:
        return redirect(order.get_absolute_url())
    if order.is_paid:
        messages.info(request, 'This order is already paid.')
        return redirect(order.get_absolute_url())

    stripe_url, stripe_error, allow_demo_payment = create_stripe_checkout(request, order)
    if stripe_url:
        return redirect(stripe_url)

    if not allow_demo_payment:
        messages.error(request, f'Stripe checkout could not be started: {stripe_error}')
        return redirect(order.get_absolute_url())

    reference = f'demo_{uuid.uuid4().hex[:12]}'
    order.mark_paid(reference)
    if not send_order_confirmation_email(order, request):
        messages.warning(request, 'Payment completed, but the confirmation email could not be sent. Check SMTP settings.')
    messages.warning(request, f'Demo card payment completed. Stripe checkout was not started: {stripe_error}')
    return redirect(order.get_absolute_url())


def payment_success(request, tracking_code):
    order = get_object_or_404(Order, tracking_code=tracking_code)
    if order.payment_method == Order.PAYMENT_CARD and not order.is_paid:
        order.mark_paid(request.GET.get('session_id', 'stripe_success'))
        if not send_order_confirmation_email(order, request):
            messages.warning(request, 'Payment completed, but the confirmation email could not be sent. Check SMTP settings.')
    messages.success(request, f'Payment received for order {order.tracking_code}.')
    return redirect(order.get_absolute_url())


def payment_cancel(request, tracking_code):
    order = get_object_or_404(Order, tracking_code=tracking_code)
    Payment.objects.update_or_create(
        order=order,
        provider='stripe',
        provider_reference=request.GET.get('session_id', ''),
        defaults={'amount': order.total, 'status': Order.PAYMENT_FAILED},
    )
    order.payment_status = Order.PAYMENT_FAILED
    order.save(update_fields=['payment_status', 'updated_at'])
    messages.warning(request, 'Payment was cancelled. You can try checkout again from order details.')
    return redirect('order_detail', tracking_code=order.tracking_code)


@csrf_exempt
def stripe_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'ok': False}, status=400)

    event_type = payload.get('type')
    session = payload.get('data', {}).get('object', {})
    if event_type == 'checkout.session.completed':
        client_reference = session.get('client_reference_id') or ''
        if client_reference.startswith('premium-'):
            payment_id = client_reference.replace('premium-', '', 1)
            if payment_id.isdigit():
                premium_payment = PremiumPayment.objects.select_related('user').filter(id=payment_id).first()
                if premium_payment and premium_payment.status != PremiumPayment.STATUS_PAID:
                    premium_payment.status = PremiumPayment.STATUS_PAID
                    premium_payment.provider_reference = session.get('id', premium_payment.provider_reference)
                    premium_payment.subscription_reference = session.get('subscription', premium_payment.subscription_reference) or ''
                    premium_payment.raw_response = {'webhook': True, 'plan': premium_payment.plan}
                    premium_payment.paid_at = timezone.now()
                    premium_payment.save(
                        update_fields=[
                            'status',
                            'provider_reference',
                            'subscription_reference',
                            'raw_response',
                            'paid_at',
                            'updated_at',
                        ]
                    )
                    activate_premium_membership(premium_payment.user, premium_payment.plan)
        else:
            order = Order.objects.filter(tracking_code=client_reference).first()
            if order and not order.is_paid:
                order.mark_paid(session.get('id', 'stripe_webhook'))
                send_order_confirmation_email(order)
    return JsonResponse({'received': True})


@login_required
def order_history(request):
    orders = request.user.orders.select_related('restaurant').prefetch_related('items')
    order_stats = {
        'total_orders': orders.count(),
        'active_orders': orders.exclude(status__in=[Order.STATUS_DELIVERED, Order.STATUS_CANCELLED]).count(),
        'total_spent': orders.aggregate(total=Sum('total'))['total'] or Decimal('0.00'),
    }
    return render(request, 'food/order_history.html', {'orders': orders, 'order_stats': order_stats})


def order_detail(request, tracking_code):
    order = get_object_or_404(Order.objects.select_related('restaurant').prefetch_related('items'), tracking_code=tracking_code)
    if request.user.is_authenticated and order.user and order.user != request.user:
        messages.error(request, 'That order belongs to a different account.')
        return redirect('order_history')
    return render(request, 'food/order_detail.html', {'order': order, 'tracking': tracking_payload(order)})


def order_tracking(request, tracking_code):
    order = get_object_or_404(Order.objects.select_related('restaurant').prefetch_related('items'), tracking_code=tracking_code)
    return render(request, 'food/order_tracking.html', {'order': order, 'tracking': tracking_payload(order)})


def order_status_api(request, tracking_code):
    order = get_object_or_404(Order, tracking_code=tracking_code)
    return JsonResponse(tracking_payload(order))


def invoice_pdf(request, tracking_code):
    order = get_object_or_404(Order.objects.select_related('restaurant').prefetch_related('items'), tracking_code=tracking_code)
    pdf = render_invoice_pdf(order)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="tonmoy-eats-invoice-{order.tracking_code}.pdf"'
    return response


@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    recent_orders = request.user.orders.select_related('restaurant')[:5]
    return render(
        request,
        'food/profile.html',
        {'user_form': user_form, 'profile_form': profile_form, 'recent_orders': recent_orders},
    )


@login_required
def premium(request):
    profile = request.user.profile
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'activate':
            plan_key = request.POST.get('plan', PremiumPayment.PLAN_MONTHLY)
            if plan_key not in PREMIUM_PLANS:
                messages.error(request, 'Please choose a valid Premium plan.')
                return redirect('premium')
            return redirect(f'{reverse("premium_payment_start")}?plan={plan_key}')
        if action == 'cancel':
            cancel_error = cancel_premium_subscription(request.user)
            profile.is_premium = False
            profile.save(update_fields=['is_premium', 'updated_at'])
            if cancel_error:
                messages.warning(request, f'Premium was cancelled locally, but Stripe renewal could not be updated: {cancel_error}')
            else:
                messages.info(request, 'Premium has been cancelled for this account.')
            return redirect('premium')

    return render(request, 'food/premium.html', {'profile': profile, 'premium_plans': premium_plan_cards()})


@login_required
def premium_payment_start(request):
    if request.user.profile.premium_active:
        messages.info(request, 'Tonmoy Eats Premium is already active on this account.')
        return redirect('premium')

    plan_key = request.POST.get('plan') or request.GET.get('plan') or PremiumPayment.PLAN_MONTHLY
    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        messages.error(request, 'Please choose a valid Premium plan.')
        return redirect('premium')

    premium_payment = PremiumPayment.objects.create(user=request.user, plan=plan_key, amount=plan['amount'])
    checkout_url, checkout_error = create_premium_stripe_checkout(request, premium_payment)
    if checkout_url:
        return redirect(checkout_url)

    premium_payment.status = PremiumPayment.STATUS_FAILED
    premium_payment.raw_response = {'error': checkout_error}
    premium_payment.save(update_fields=['status', 'raw_response', 'updated_at'])
    messages.error(request, f'Premium payment could not be started: {checkout_error}')
    return redirect('premium')


@login_required
def premium_payment_success(request):
    session_id = request.GET.get('session_id', '').strip()
    if not session_id:
        messages.error(request, 'Premium payment session was missing. Please try again.')
        return redirect('premium')

    premium_payment = get_object_or_404(PremiumPayment, provider_reference=session_id, user=request.user)
    if premium_payment.status != PremiumPayment.STATUS_PAID:
        premium_payment.status = PremiumPayment.STATUS_PAID
        premium_payment.paid_at = timezone.now()
        session_data = retrieve_stripe_checkout_session(session_id)
        subscription_reference = session_data.get('subscription', '') if session_data else ''
        if subscription_reference:
            premium_payment.subscription_reference = subscription_reference
        raw_response = premium_payment.raw_response or {}
        raw_response.update({'success': True, 'plan': premium_payment.plan})
        if subscription_reference:
            raw_response['subscription_reference'] = subscription_reference
        premium_payment.raw_response = raw_response
        premium_payment.save(
            update_fields=['status', 'subscription_reference', 'raw_response', 'paid_at', 'updated_at']
        )

    activate_premium_membership(request.user, premium_payment.plan)
    plan = PREMIUM_PLANS.get(premium_payment.plan, PREMIUM_PLANS[PremiumPayment.PLAN_MONTHLY])
    messages.success(request, f'Payment received. Tonmoy Eats Premium is now active for {plan["duration_text"]}.')
    return redirect('premium')


@login_required
def premium_payment_cancel(request):
    payment_id = request.GET.get('payment_id', '').strip()
    premium_payment = None
    if payment_id.isdigit():
        premium_payment = PremiumPayment.objects.filter(id=payment_id, user=request.user).first()
    if premium_payment and premium_payment.status == PremiumPayment.STATUS_PENDING:
        premium_payment.status = PremiumPayment.STATUS_FAILED
        premium_payment.raw_response = {'cancelled': True}
        premium_payment.save(update_fields=['status', 'raw_response', 'updated_at'])

    messages.warning(request, 'Premium payment was cancelled. You can try again anytime.')
    return redirect('premium')


def activate_premium_membership(user, plan_key=PremiumPayment.PLAN_MONTHLY):
    plan = PREMIUM_PLANS.get(plan_key, PREMIUM_PLANS[PremiumPayment.PLAN_MONTHLY])
    profile = user.profile
    now = timezone.now()
    profile.is_premium = True
    profile.premium_plan = plan_key
    profile.premium_started_at = profile.premium_started_at or now
    profile.premium_expires_at = now + timedelta(days=plan['duration_days'])
    profile.save(update_fields=['is_premium', 'premium_plan', 'premium_started_at', 'premium_expires_at', 'updated_at'])


def premium_plan_cards():
    return [
        {
            'key': key,
            'price': plan['amount'],
            'featured': plan.get('featured', False),
            **plan,
        }
        for key, plan in PREMIUM_PLANS.items()
    ]


def cancel_premium_subscription(user):
    premium_payment = (
        user.premium_payments.filter(status=PremiumPayment.STATUS_PAID, subscription_reference__gt='')
        .order_by('-paid_at', '-created_at')
        .first()
    )
    if not premium_payment:
        return ''
    if not settings.STRIPE_SECRET_KEY:
        return 'missing STRIPE_SECRET_KEY'
    try:
        import stripe
    except ImportError:
        return 'the stripe Python package is not installed'

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        stripe.Subscription.modify(premium_payment.subscription_reference, cancel_at_period_end=True)
    except Exception as exc:
        return str(exc)

    raw_response = premium_payment.raw_response or {}
    raw_response['cancel_at_period_end'] = True
    premium_payment.raw_response = raw_response
    premium_payment.save(update_fields=['raw_response', 'updated_at'])
    return ''


def csrf_failure(request, reason=''):
    login_path = reverse('login')
    register_path = reverse('register')
    if request.path.startswith(login_path):
        return redirect(f'{login_path}?csrf=expired')
    if request.path.startswith(register_path):
        return redirect(f'{register_path}?csrf=expired')
    return redirect(f'{reverse("home")}?csrf=expired')


@never_cache
def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.GET.get('csrf') == 'expired':
        messages.warning(request, 'Security token expired. Please submit the refreshed form again.')

    pending_data = request.session.get('register_otp_data') or {}
    registration_otp_pending = bool(pending_data)
    registration_otp_email = pending_data.get('email', '')
    initial = registration_initial_from_pending(pending_data)

    if request.method == 'POST':
        action = request.POST.get('action', 'start_registration')
        if action == 'verify_registration_otp':
            form = RegisterForm(initial=initial)
            otp_code = request.POST.get('registration_otp_code', '').strip()
            expected_code = request.session.get('register_otp_code')
            expires = request.session.get('register_otp_expires', 0)

            if not pending_data or not expected_code:
                clear_registration_otp(request)
                registration_otp_pending = False
                registration_otp_email = ''
                form = RegisterForm()
                messages.error(request, 'Please submit the register form and request a new OTP first.')
            elif otp_is_expired(expires):
                clear_registration_otp(request)
                registration_otp_pending = False
                registration_otp_email = ''
                form = RegisterForm(initial=initial)
                messages.error(request, 'That registration OTP has expired. Please request a new one.')
            elif otp_code != expected_code:
                messages.error(request, 'Invalid OTP. Please check the code and try again.')
            elif User.objects.filter(username__iexact=pending_data['username']).exists():
                clear_registration_otp(request)
                registration_otp_pending = False
                registration_otp_email = ''
                form = RegisterForm(initial=initial)
                messages.error(request, 'That username was just taken. Please choose another one.')
            elif User.objects.filter(email__iexact=pending_data['email']).exists():
                clear_registration_otp(request)
                registration_otp_pending = False
                registration_otp_email = ''
                form = RegisterForm(initial=initial)
                messages.error(request, 'An account already exists with that email. Please login instead.')
            else:
                user = User.objects.create(
                    username=pending_data['username'],
                    email=pending_data['email'],
                    first_name=pending_data['first_name'],
                    last_name=pending_data['last_name'],
                    password=pending_data['password_hash'],
                )
                login(request, user)
                clear_registration_otp(request)
                messages.success(request, 'Your account is verified and ready.')
                return redirect('home')
        else:
            form = RegisterForm(request.POST)
            if form.is_valid():
                otp_code = generate_otp_code()
                pending_data = {
                    'first_name': form.cleaned_data['first_name'],
                    'last_name': form.cleaned_data['last_name'],
                    'username': form.cleaned_data['username'],
                    'email': form.cleaned_data['email'],
                    'password_hash': make_password(form.cleaned_data['password1']),
                }
                request.session['register_otp_data'] = pending_data
                request.session['register_otp_code'] = otp_code
                request.session['register_otp_expires'] = (timezone.now() + timedelta(minutes=10)).timestamp()
                request.session.modified = True
                email_sent = send_register_otp_email(
                    pending_data['email'],
                    pending_data['first_name'],
                    otp_code,
                )
                if email_sent:
                    messages.success(
                        request,
                        f'Registration OTP sent to {mask_email(pending_data["email"])}. It is valid for 10 minutes.',
                    )
                else:
                    clear_registration_otp(request)
                    messages.warning(request, 'OTP could not be sent. Check SMTP settings and try again.')
                    registration_otp_pending = False
                    registration_otp_email = ''
                    pending_data = {}
                if email_sent:
                    registration_otp_pending = True
                    registration_otp_email = pending_data['email']
                form = RegisterForm(initial=registration_initial_from_pending(pending_data))
    else:
        form = RegisterForm(initial=initial)
    return render(
        request,
        'registration/register.html',
        {
            'form': form,
            'registration_otp_pending': registration_otp_pending,
            'registration_otp_email': registration_otp_email,
        },
    )


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.GET.get('csrf') == 'expired':
        messages.warning(request, 'Security token expired. Please submit the refreshed form again.')

    password_form = AuthenticationForm(request, data=request.POST or None)
    otp_email = request.session.get('login_otp_email', '')
    otp_pending = bool(request.session.get('login_otp_code'))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'password_login':
            password_form = AuthenticationForm(request, data=request.POST)
            if password_form.is_valid():
                user = password_form.get_user()
                otp_started, otp_email = start_login_otp(request, user)
                otp_pending = otp_started
                if otp_started:
                    messages.success(
                        request,
                        f'Password verified. OTP sent to {mask_email(otp_email)}.',
                    )
                else:
                    messages.error(request, 'Password verified, but OTP could not be sent. Add an email and check SMTP settings.')
        elif action == 'send_otp':
            email = request.POST.get('otp_email', '').strip().lower()
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if not user:
                messages.error(request, 'No active account was found with that email. Please register first.')
            elif not user.email:
                messages.error(request, 'This account does not have an email address.')
            else:
                otp_started, otp_email = start_login_otp(request, user)
                otp_pending = otp_started
                if otp_started:
                    messages.success(
                        request,
                        f'OTP sent to {mask_email(otp_email)}. It is valid for 10 minutes.',
                    )
                else:
                    messages.error(request, 'OTP could not be sent. Add an email and check SMTP settings.')
        elif action == 'verify_otp':
            otp_code = request.POST.get('otp_code', '').strip()
            user_id = request.session.get('login_otp_user_id')
            expected_code = request.session.get('login_otp_code')
            expires = request.session.get('login_otp_expires', 0)
            if not user_id or not expected_code:
                messages.error(request, 'Please request a new OTP first.')
            elif otp_is_expired(expires):
                clear_login_otp(request)
                otp_pending = False
                otp_email = ''
                messages.error(request, 'That OTP has expired. Please request a new one.')
            elif otp_code != expected_code:
                messages.error(request, 'Invalid OTP. Please check the code and try again.')
            else:
                user = get_object_or_404(User, id=user_id, is_active=True)
                login(request, user)
                clear_login_otp(request)
                messages.success(request, 'Logged in successfully with OTP.')
                return redirect(request.GET.get('next') or 'home')

    style_login_form(password_form)
    context = {
            'form': password_form,
            'otp_email': otp_email,
            'otp_email_display': mask_email(otp_email),
            'otp_pending': otp_pending,
    }
    return render(request, 'registration/login.html', context)


def generate_otp_code():
    return str(random.SystemRandom().randint(100000, 999999))


def start_login_otp(request, user):
    otp_code = generate_otp_code()
    email_sent = send_login_otp_email(user, otp_code)
    if not email_sent:
        clear_login_otp(request)
        return False, ''

    delivered_email = user.email
    request.session['login_otp_user_id'] = user.id
    request.session['login_otp_email'] = delivered_email
    request.session['login_otp_code'] = otp_code
    request.session['login_otp_expires'] = (timezone.now() + timedelta(minutes=10)).timestamp()
    request.session.modified = True
    return True, delivered_email


def clear_login_otp(request):
    for key in ['login_otp_user_id', 'login_otp_email', 'login_otp_code', 'login_otp_expires']:
        request.session.pop(key, None)
    request.session.modified = True


def clear_registration_otp(request):
    for key in ['register_otp_data', 'register_otp_code', 'register_otp_expires']:
        request.session.pop(key, None)
    request.session.modified = True


def registration_initial_from_pending(pending_data):
    return {
        'first_name': pending_data.get('first_name', ''),
        'last_name': pending_data.get('last_name', ''),
        'username': pending_data.get('username', ''),
        'email': pending_data.get('email', ''),
    }


def otp_is_expired(expires):
    try:
        return timezone.now().timestamp() > float(expires)
    except (TypeError, ValueError):
        return True


def style_login_form(form):
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'form-input')


def mask_email(email):
    if not email or '@' not in email:
        return ''
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = f'{local[:1]}***'
    else:
        masked_local = f'{local[:2]}***{local[-1:]}'
    return f'{masked_local}@{domain}'


def request_payload(request):
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return {}
    return request.POST


def sync_profile_from_checkout(user, data):
    User.objects.filter(pk=user.pk).update(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
    )
    profile = user.profile
    profile.phone = data['phone']
    profile.address = data['address']
    profile.city = data['city']
    profile.postcode = data['postcode']
    profile.delivery_notes = data['delivery_notes']
    profile.save()


def create_stripe_checkout(request, order):
    if not settings.STRIPE_SECRET_KEY:
        return None, 'missing STRIPE_SECRET_KEY in settings.py or environment.', True
    try:
        import stripe
    except ImportError:
        return None, 'the stripe Python package is not installed. Run python -m pip install -r requirements.txt.', True

    stripe.api_key = settings.STRIPE_SECRET_KEY
    success_url = request.build_absolute_uri(reverse('payment_success', kwargs={'tracking_code': order.tracking_code}))
    cancel_url = request.build_absolute_uri(reverse('payment_cancel', kwargs={'tracking_code': order.tracking_code}))
    try:
        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            client_reference_id=order.tracking_code,
            customer_email=order.email,
            line_items=[
                {
                    'price_data': {
                        'currency': 'inr',
                        'product_data': {'name': f'Tonmoy Eats order {order.tracking_code}'},
                        'unit_amount': int(order.total * 100),
                    },
                    'quantity': 1,
                }
            ],
            success_url=f'{success_url}?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=cancel_url,
        )
    except Exception as exc:
        return None, str(exc), False
    Payment.objects.update_or_create(
        order=order,
        provider='stripe',
        provider_reference=session.id,
        defaults={'amount': order.total, 'status': Order.PAYMENT_PENDING, 'raw_response': {'url': session.url}},
    )
    return session.url, '', False


def create_premium_stripe_checkout(request, premium_payment):
    if not settings.STRIPE_SECRET_KEY:
        return None, 'missing STRIPE_SECRET_KEY in settings.py or environment.'
    try:
        import stripe
    except ImportError:
        return None, 'the stripe Python package is not installed. Run python -m pip install -r requirements.txt.'

    stripe.api_key = settings.STRIPE_SECRET_KEY
    plan = PREMIUM_PLANS.get(premium_payment.plan, PREMIUM_PLANS[PremiumPayment.PLAN_MONTHLY])
    success_url = request.build_absolute_uri(reverse('premium_payment_success'))
    cancel_url = request.build_absolute_uri(f'{reverse("premium_payment_cancel")}?payment_id={premium_payment.id}')
    checkout_kwargs = {
        'mode': 'subscription',
        'payment_method_types': ['card'],
        'client_reference_id': f'premium-{premium_payment.id}',
        'line_items': [
            {
                'price_data': {
                    'currency': 'inr',
                    'product_data': {'name': f'Tonmoy Eats Premium - {plan["name"]}'},
                    'unit_amount': int(premium_payment.amount * Decimal('100')),
                    'recurring': {'interval': plan['interval']},
                },
                'quantity': 1,
            }
        ],
        'success_url': f'{success_url}?session_id={{CHECKOUT_SESSION_ID}}',
        'cancel_url': cancel_url,
        'metadata': {
            'premium_payment_id': str(premium_payment.id),
            'user_id': str(request.user.id),
            'plan': premium_payment.plan,
        },
    }
    if request.user.email:
        checkout_kwargs['customer_email'] = request.user.email

    try:
        session = stripe.checkout.Session.create(**checkout_kwargs)
    except Exception as exc:
        return None, str(exc)

    premium_payment.provider_reference = session.id
    premium_payment.raw_response = {'url': session.url}
    premium_payment.save(update_fields=['provider_reference', 'raw_response', 'updated_at'])
    return session.url, ''


def retrieve_stripe_checkout_session(session_id):
    if not settings.STRIPE_SECRET_KEY:
        return {}
    try:
        import stripe
    except ImportError:
        return {}

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        return {}
    return {
        'id': getattr(session, 'id', ''),
        'subscription': getattr(session, 'subscription', '') or '',
        'payment_status': getattr(session, 'payment_status', ''),
    }
