from django.contrib import admin, messages

from .models import Category, MenuItem, Order, OrderItem, Payment, PremiumPayment, Restaurant, UserProfile
from .utils import send_order_status_email


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'cuisine', 'city', 'rating', 'delivery_time', 'is_active', 'is_featured')
    list_filter = ('is_active', 'is_featured', 'city', 'cuisine')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'cuisine', 'city')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'image_url')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'is_available', 'is_featured')
    list_filter = ('restaurant', 'category', 'is_available', 'is_featured')
    search_fields = ('name', 'description', 'restaurant__name')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('menu_item', 'name', 'price', 'quantity', 'line_total')


@admin.action(description='Mark selected orders as confirmed')
def mark_confirmed(modeladmin, request, queryset):
    _set_order_status(request, queryset, Order.STATUS_CONFIRMED)


@admin.action(description='Mark selected orders as preparing')
def mark_preparing(modeladmin, request, queryset):
    _set_order_status(request, queryset, Order.STATUS_PREPARING)


@admin.action(description='Mark selected orders as out for delivery')
def mark_out_for_delivery(modeladmin, request, queryset):
    _set_order_status(request, queryset, Order.STATUS_OUT_FOR_DELIVERY)


@admin.action(description='Mark selected orders as delivered')
def mark_delivered(modeladmin, request, queryset):
    _set_order_status(request, queryset, Order.STATUS_DELIVERED)


def _set_order_status(request, queryset, status):
    count = 0
    for order in queryset:
        order.status = status
        order.save(update_fields=['status', 'updated_at'])
        send_order_status_email(order)
        count += 1
    messages.success(request, f'{count} orders updated.')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'customer_name', 'restaurant', 'status', 'payment_status', 'total', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'restaurant')
    search_fields = ('tracking_code', 'email', 'phone', 'first_name', 'last_name')
    readonly_fields = ('tracking_code', 'subtotal', 'delivery_fee', 'tax', 'discount', 'total', 'paid_at', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    actions = [mark_confirmed, mark_preparing, mark_out_for_delivery, mark_delivered]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'provider', 'amount', 'status', 'provider_reference', 'created_at')
    list_filter = ('provider', 'status')
    search_fields = ('order__tracking_code', 'provider_reference')


@admin.register(PremiumPayment)
class PremiumPaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'amount', 'status', 'provider', 'provider_reference', 'subscription_reference', 'paid_at', 'created_at')
    list_filter = ('plan', 'status', 'provider')
    search_fields = ('user__username', 'user__email', 'provider_reference', 'subscription_reference')
    readonly_fields = ('created_at', 'updated_at', 'paid_at', 'raw_response')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city', 'postcode', 'is_premium', 'premium_plan', 'premium_expires_at')
    list_filter = ('is_premium', 'premium_plan', 'city')
    search_fields = ('user__username', 'user__email', 'phone', 'city')
