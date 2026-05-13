from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('restaurants/', views.restaurant_list, name='restaurant_list'),
    path('restaurants/<slug:slug>/', views.restaurant_detail, name='restaurant_detail'),
    path('cart/', views.cart_page, name='cart'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/update/', views.cart_update, name='cart_update'),
    path('cart/remove/', views.cart_remove, name='cart_remove'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<str:tracking_code>/', views.payment_start, name='payment_start'),
    path('payment/success/<str:tracking_code>/', views.payment_success, name='payment_success'),
    path('payment/cancel/<str:tracking_code>/', views.payment_cancel, name='payment_cancel'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<str:tracking_code>/', views.order_detail, name='order_detail'),
    path('track/<str:tracking_code>/', views.order_tracking, name='order_tracking'),
    path('track/<str:tracking_code>/status/', views.order_status_api, name='order_status_api'),
    path('invoice/<str:tracking_code>/', views.invoice_pdf, name='invoice_pdf'),
    path('profile/', views.profile, name='profile'),
    path('premium/payment/', views.premium_payment_start, name='premium_payment_start'),
    path('premium/payment/success/', views.premium_payment_success, name='premium_payment_success'),
    path('premium/payment/cancel/', views.premium_payment_cancel, name='premium_payment_cancel'),
    path('premium/', views.premium, name='premium'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
