import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


PREMIUM_PLAN_WEEKLY = 'weekly'
PREMIUM_PLAN_MONTHLY = 'monthly'
PREMIUM_PLAN_ANNUAL = 'annual'

PREMIUM_PLAN_CHOICES = [
    (PREMIUM_PLAN_WEEKLY, 'Weekly'),
    (PREMIUM_PLAN_MONTHLY, 'Monthly'),
    (PREMIUM_PLAN_ANNUAL, 'Annual'),
]

PREMIUM_DISCOUNT_RATES = {
    PREMIUM_PLAN_WEEKLY: Decimal('0.05'),
    PREMIUM_PLAN_MONTHLY: Decimal('0.20'),
    PREMIUM_PLAN_ANNUAL: Decimal('0.25'),
}


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Restaurant(TimeStampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    tagline = models.CharField(max_length=180)
    description = models.TextField()
    cuisine = models.CharField(max_length=90)
    city = models.CharField(max_length=80)
    address = models.CharField(max_length=220)
    phone = models.CharField(max_length=30)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('4.5'))
    delivery_time = models.PositiveIntegerField(help_text='Estimated delivery time in minutes')
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    minimum_order = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    cover_image = models.URLField(blank=True)
    logo_image = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_featured', '-rating', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            index = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                index += 1
                slug = f'{base_slug}-{index}'
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('restaurant_detail', kwargs={'slug': self.slug})

    @property
    def is_open_now(self):
        now = timezone.localtime().time()
        if self.opening_time <= self.closing_time:
            return self.opening_time <= now <= self.closing_time
        return now >= self.opening_time or now <= self.closing_time


class Category(TimeStampedModel):
    name = models.CharField(max_length=90, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.CharField(max_length=180, blank=True)
    icon = models.CharField(max_length=40, blank=True)
    image_url = models.URLField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MenuItem(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, related_name='menu_items', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='menu_items', on_delete=models.PROTECT)
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=180, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image_url = models.URLField(blank=True)
    calories = models.PositiveIntegerField(default=0)
    spicy_level = models.PositiveSmallIntegerField(default=0)
    labels = models.CharField(max_length=180, blank=True, help_text='Comma separated labels')
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ['category__name', 'name']
        unique_together = ('restaurant', 'slug')

    def __str__(self):
        return f'{self.name} - {self.restaurant.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            index = 1
            while MenuItem.objects.filter(restaurant=self.restaurant, slug=slug).exclude(pk=self.pk).exists():
                index += 1
                slug = f'{base_slug}-{index}'
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def label_list(self):
        return [label.strip() for label in self.labels.split(',') if label.strip()]


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=220, blank=True)
    city = models.CharField(max_length=80, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    avatar_url = models.URLField(blank=True)
    delivery_notes = models.CharField(max_length=220, blank=True)
    is_premium = models.BooleanField(default=False)
    premium_plan = models.CharField(max_length=20, choices=PREMIUM_PLAN_CHOICES, default=PREMIUM_PLAN_MONTHLY)
    premium_started_at = models.DateTimeField(null=True, blank=True)
    premium_expires_at = models.DateTimeField(null=True, blank=True)

    @property
    def premium_active(self):
        if not self.is_premium:
            return False
        if not self.premium_expires_at:
            return True
        return self.premium_expires_at >= timezone.now()

    @property
    def premium_discount_rate(self):
        return PREMIUM_DISCOUNT_RATES.get(self.premium_plan, PREMIUM_DISCOUNT_RATES[PREMIUM_PLAN_MONTHLY])

    @property
    def premium_discount_percent(self):
        return int(self.premium_discount_rate * 100)

    def __str__(self):
        return f'{self.user.username} profile'


class PremiumPayment(TimeStampedModel):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    PLAN_WEEKLY = PREMIUM_PLAN_WEEKLY
    PLAN_MONTHLY = PREMIUM_PLAN_MONTHLY
    PLAN_ANNUAL = PREMIUM_PLAN_ANNUAL

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
    ]
    PLAN_CHOICES = PREMIUM_PLAN_CHOICES

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='premium_payments', on_delete=models.CASCADE)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_MONTHLY)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('99.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    provider = models.CharField(max_length=40, default='stripe')
    provider_reference = models.CharField(max_length=180, blank=True)
    subscription_reference = models.CharField(max_length=180, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Premium payment for {self.user.username} - {self.status}'


class Order(TimeStampedModel):
    STATUS_PLACED = 'placed'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_PREPARING = 'preparing'
    STATUS_OUT_FOR_DELIVERY = 'out_for_delivery'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    PAYMENT_PENDING = 'pending'
    PAYMENT_PAID = 'paid'
    PAYMENT_FAILED = 'failed'
    PAYMENT_REFUNDED = 'refunded'

    PAYMENT_COD = 'cod'
    PAYMENT_CARD = 'card'

    STATUS_CHOICES = [
        (STATUS_PLACED, 'Placed'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_PREPARING, 'Preparing'),
        (STATUS_OUT_FOR_DELIVERY, 'Out for delivery'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_PAID, 'Paid'),
        (PAYMENT_FAILED, 'Failed'),
        (PAYMENT_REFUNDED, 'Refunded'),
    ]
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_COD, 'Cash on delivery'),
        (PAYMENT_CARD, 'Card payment'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', null=True, blank=True, on_delete=models.SET_NULL)
    restaurant = models.ForeignKey(Restaurant, related_name='orders', on_delete=models.PROTECT)
    tracking_code = models.CharField(max_length=18, unique=True, editable=False)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=220)
    city = models.CharField(max_length=80)
    postcode = models.CharField(max_length=20)
    delivery_notes = models.CharField(max_length=220, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PLACED)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order {self.tracking_code}'

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('order_tracking', kwargs={'tracking_code': self.tracking_code})

    @property
    def customer_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_paid(self):
        return self.payment_status == self.PAYMENT_PAID

    def mark_paid(self, reference=''):
        self.payment_status = self.PAYMENT_PAID
        self.paid_at = timezone.now()
        self.save(update_fields=['payment_status', 'paid_at', 'updated_at'])
        if reference:
            Payment.objects.update_or_create(
                order=self,
                provider_reference=reference,
                defaults={
                    'provider': 'stripe' if reference.startswith('cs_') else 'demo-card',
                    'amount': self.total,
                    'status': self.PAYMENT_PAID,
                },
            )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=140)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=9, decimal_places=2)

    def __str__(self):
        return f'{self.quantity} x {self.name}'


class Payment(TimeStampedModel):
    order = models.ForeignKey(Order, related_name='payments', on_delete=models.CASCADE)
    provider = models.CharField(max_length=40)
    provider_reference = models.CharField(max_length=180, blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    status = models.CharField(max_length=20, choices=Order.PAYMENT_STATUS_CHOICES, default=Order.PAYMENT_PENDING)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.provider} payment for {self.order.tracking_code}'
