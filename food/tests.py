from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .cart import Cart
from .models import Category, MenuItem, Order, OrderItem, PremiumPayment, Restaurant
from .utils import send_order_confirmation_email


class FoodFlowTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Pizza', slug='pizza')
        self.restaurant = Restaurant.objects.create(
            name='Test Kitchen',
            tagline='Fresh test meals',
            description='A restaurant used for automated tests.',
            cuisine='Italian',
            city='Kolkata',
            address='42 Test Street',
            phone='1234567890',
            opening_time='09:00',
            closing_time='23:00',
            delivery_time=25,
            delivery_fee=Decimal('2.50'),
            minimum_order=Decimal('5.00'),
        )
        self.item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name='Margherita',
            description='Tomato, mozzarella, basil.',
            price=Decimal('8.00'),
        )

    def test_cart_totals(self):
        request = RequestFactory().get('/')
        request.session = self.client.session
        cart = Cart(request)
        cart.add(self.item, quantity=2)

        self.assertEqual(cart.count, 2)
        self.assertEqual(cart.subtotal, Decimal('16.00'))
        self.assertEqual(cart.delivery_fee, Decimal('2.50'))
        self.assertEqual(cart.tax, Decimal('0.80'))
        self.assertEqual(cart.total, Decimal('19.30'))

    def test_premium_cart_gets_discount_and_free_delivery(self):
        user = User.objects.create_user(username='premiumbuyer', password='secret')
        user.profile.is_premium = True
        user.profile.premium_started_at = timezone.now()
        user.profile.premium_expires_at = timezone.now() + timedelta(days=30)
        user.profile.save()
        request = RequestFactory().get('/')
        request.session = self.client.session
        request.user = user
        cart = Cart(request)
        cart.add(self.item, quantity=2)

        self.assertTrue(cart.premium_active)
        self.assertEqual(cart.premium_discount_percent, 20)
        self.assertEqual(cart.subtotal, Decimal('16.00'))
        self.assertEqual(cart.delivery_fee, Decimal('0.00'))
        self.assertEqual(cart.discount, Decimal('3.20'))
        self.assertEqual(cart.tax, Decimal('0.64'))
        self.assertEqual(cart.total, Decimal('13.44'))

    def test_weekly_premium_cart_gets_five_percent_discount(self):
        user = User.objects.create_user(username='weeklybuyer', password='secret')
        user.profile.is_premium = True
        user.profile.premium_plan = PremiumPayment.PLAN_WEEKLY
        user.profile.premium_started_at = timezone.now()
        user.profile.premium_expires_at = timezone.now() + timedelta(days=7)
        user.profile.save()
        request = RequestFactory().get('/')
        request.session = self.client.session
        request.user = user
        cart = Cart(request)
        cart.add(self.item, quantity=2)

        self.assertTrue(cart.premium_active)
        self.assertEqual(cart.premium_discount_percent, 5)
        self.assertEqual(cart.discount, Decimal('0.80'))
        self.assertEqual(cart.tax, Decimal('0.76'))
        self.assertEqual(cart.total, Decimal('15.96'))

    def test_annual_premium_cart_gets_twenty_five_percent_discount(self):
        user = User.objects.create_user(username='annualbuyer', password='secret')
        user.profile.is_premium = True
        user.profile.premium_plan = PremiumPayment.PLAN_ANNUAL
        user.profile.premium_started_at = timezone.now()
        user.profile.premium_expires_at = timezone.now() + timedelta(days=365)
        user.profile.save()
        request = RequestFactory().get('/')
        request.session = self.client.session
        request.user = user
        cart = Cart(request)
        cart.add(self.item, quantity=2)

        self.assertTrue(cart.premium_active)
        self.assertEqual(cart.premium_discount_percent, 25)
        self.assertEqual(cart.discount, Decimal('4.00'))
        self.assertEqual(cart.tax, Decimal('0.60'))
        self.assertEqual(cart.total, Decimal('12.60'))

    def test_restaurant_list_loads(self):
        response = self.client.get(reverse('restaurant_list'), {'q': 'pizza'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Kitchen')

    def test_order_history_requires_login(self):
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_cart_add_requires_login(self):
        response = self.client.post(
            reverse('cart_add'),
            data={'item_id': self.item.id, 'quantity': 1},
        )

        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.json()['login_required'])

    def test_email_otp_login_flow(self):
        user = User.objects.create_user(
            username='otpbuyer',
            password='secret',
            email='otp@example.com',
            first_name='Otp',
        )

        response = self.client.post(
            reverse('login'),
            data={'action': 'send_otp', 'otp_email': user.email},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('login OTP', mail.outbox[0].subject)

        session = self.client.session
        otp_code = session['login_otp_code']
        response = self.client.post(
            reverse('login'),
            data={'action': 'verify_otp', 'otp_code': otp_code},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_password_login_sends_otp_before_login(self):
        user = User.objects.create_user(
            username='securebuyer',
            password='secret',
            email='secure@example.com',
            first_name='Secure',
        )

        response = self.client.post(
            reverse('login'),
            data={'action': 'password_login', 'username': 'securebuyer', 'password': 'secret'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Enter 6 digit OTP')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('login OTP', mail.outbox[0].subject)

        otp_code = self.client.session['login_otp_code']
        response = self.client.post(
            reverse('login'),
            data={'action': 'verify_otp', 'otp_code': otp_code},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_login_csrf_failure_redirects_to_refreshed_login(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(
            reverse('login'),
            data={'action': 'password_login', 'username': 'buyer', 'password': 'secret'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'{reverse("login")}?csrf=expired')

    def test_register_requires_email_otp_then_logs_in(self):
        registration_data = {
            'action': 'start_registration',
            'first_name': 'Reg',
            'last_name': 'Buyer',
            'username': 'regbuyer',
            'email': 'regbuyer@example.com',
            'password1': 'VeryStrongPass123!',
            'password2': 'VeryStrongPass123!',
        }

        response = self.client.post(reverse('register'), data=registration_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verify your email')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify your Tonmoy Eats account', mail.outbox[0].subject)
        self.assertFalse(User.objects.filter(username='regbuyer').exists())

        otp_code = self.client.session['register_otp_code']
        response = self.client.post(
            reverse('register'),
            data={'action': 'verify_registration_otp', 'registration_otp_code': otp_code},
        )

        user = User.objects.get(username='regbuyer')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_premium_checkout_saves_discount_on_order(self):
        user = User.objects.create_user(
            username='premiumorder',
            password='secret',
            email='premium@example.com',
            first_name='Premium',
            last_name='Buyer',
        )
        user.profile.is_premium = True
        user.profile.premium_started_at = timezone.now()
        user.profile.premium_expires_at = timezone.now() + timedelta(days=30)
        user.profile.phone = '1234567890'
        user.profile.address = '42 Premium Street'
        user.profile.city = 'Tezpur'
        user.profile.postcode = '784001'
        user.profile.save()
        self.client.force_login(user)
        self.client.post(reverse('cart_add'), data={'item_id': self.item.id, 'quantity': 2})

        response = self.client.post(
            reverse('checkout'),
            data={
                'first_name': 'Premium',
                'last_name': 'Buyer',
                'email': 'premium@example.com',
                'phone': '1234567890',
                'address': '42 Premium Street',
                'city': 'Tezpur',
                'postcode': '784001',
                'delivery_notes': '',
                'payment_method': Order.PAYMENT_COD,
            },
        )

        order = Order.objects.get(email='premium@example.com')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(order.delivery_fee, Decimal('0.00'))
        self.assertEqual(order.discount, Decimal('3.20'))
        self.assertEqual(order.total, Decimal('13.44'))

    def test_premium_page_activation_redirects_to_payment(self):
        user = User.objects.create_user(username='joinpremium', password='secret')
        self.client.force_login(user)

        response = self.client.post(reverse('premium'), data={'action': 'activate'})

        user.profile.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'{reverse("premium_payment_start")}?plan={PremiumPayment.PLAN_MONTHLY}')
        self.assertFalse(user.profile.premium_active)

    @patch('food.views.create_premium_stripe_checkout', return_value=('https://checkout.stripe.test/session', ''))
    def test_premium_payment_start_creates_checkout_session(self, mocked_checkout):
        user = User.objects.create_user(username='premiumstripe', password='secret', email='premiumstripe@example.com')
        self.client.force_login(user)

        response = self.client.post(reverse('premium_payment_start'), data={'plan': PremiumPayment.PLAN_ANNUAL})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://checkout.stripe.test/session')
        premium_payment = PremiumPayment.objects.get(user=user)
        self.assertEqual(premium_payment.plan, PremiumPayment.PLAN_ANNUAL)
        self.assertEqual(premium_payment.amount, Decimal('999.00'))
        mocked_checkout.assert_called_once()

    @patch('food.views.retrieve_stripe_checkout_session', return_value={})
    def test_premium_payment_success_enables_membership(self, mocked_retrieve):
        user = User.objects.create_user(username='paidpremium', password='secret', email='paidpremium@example.com')
        premium_payment = PremiumPayment.objects.create(
            user=user,
            plan=PremiumPayment.PLAN_WEEKLY,
            amount=Decimal('29.00'),
            provider_reference='cs_test_premium',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('premium_payment_success'), {'session_id': 'cs_test_premium'})

        user.profile.refresh_from_db()
        premium_payment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('premium'))
        self.assertTrue(user.profile.premium_active)
        self.assertEqual(user.profile.premium_plan, PremiumPayment.PLAN_WEEKLY)
        self.assertEqual(user.profile.premium_discount_percent, 5)
        self.assertIsNotNone(user.profile.premium_expires_at)
        self.assertEqual(premium_payment.status, PremiumPayment.STATUS_PAID)

    def test_premium_cancel_uses_confirmation_modal(self):
        user = User.objects.create_user(username='cancelpremium', password='secret')
        user.profile.is_premium = True
        user.profile.premium_started_at = timezone.now()
        user.profile.premium_expires_at = timezone.now() + timedelta(days=30)
        user.profile.save()
        self.client.force_login(user)

        response = self.client.get(reverse('premium'))

        self.assertContains(response, 'data-premium-cancel-modal')
        self.assertContains(response, 'Yes, cancel Premium')

    def test_invoice_endpoint_returns_pdf(self):
        order = self.create_order()

        response = self.client.get(reverse('invoice_pdf', kwargs={'tracking_code': order.tracking_code}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_order_confirmation_email_attaches_invoice_pdf(self):
        order = self.create_order()

        send_order_confirmation_email(order)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn(order.email, message.to)
        self.assertIn(order.tracking_code, message.subject)
        self.assertEqual(len(message.attachments), 1)
        filename, content, mimetype = message.attachments[0]
        self.assertEqual(filename, f'tonmoy-eats-invoice-{order.tracking_code}.pdf')
        self.assertEqual(mimetype, 'application/pdf')
        self.assertTrue(content.startswith(b'%PDF'))

    def create_order(self):
        user = User.objects.create_user(username='buyer', password='secret')
        order = Order.objects.create(
            user=user,
            restaurant=self.restaurant,
            first_name='Test',
            last_name='Buyer',
            email='buyer@example.com',
            phone='1234567890',
            address='42 Test Street',
            city='Kolkata',
            postcode='700001',
            payment_method=Order.PAYMENT_COD,
            subtotal=Decimal('8.00'),
            delivery_fee=Decimal('2.50'),
            tax=Decimal('0.40'),
            total=Decimal('10.90'),
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item,
            name=self.item.name,
            price=self.item.price,
            quantity=1,
            line_total=self.item.price,
        )
        return order
