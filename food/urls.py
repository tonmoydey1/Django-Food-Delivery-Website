from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import StyledPasswordResetForm, StyledSetPasswordForm

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
    path('forgot-username/', views.forgot_username, name='forgot_username'),
    path('forgot-username/done/', views.forgot_username_done, name='forgot_username_done'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='food/registration/password_reset_form.html',
            email_template_name='food/registration/password_reset_email.txt',
            html_email_template_name='food/registration/password_reset_email.html',
            subject_template_name='food/registration/password_reset_subject.txt',
            form_class=StyledPasswordResetForm,
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='food/registration/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='food/registration/password_reset_confirm.html',
            form_class=StyledSetPasswordForm,
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='food/registration/password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
