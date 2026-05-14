from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Order, UserProfile


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styles(self)


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styles(self)


class UsernameReminderForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs={'inputmode': 'email'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styles(self)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=80)
    last_name = forms.CharField(max_length=80)
    email = forms.EmailField(widget=forms.TextInput(attrs={'inputmode': 'email'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styles(self)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already exists with this email.')
        return email


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.TextInput(attrs={'inputmode': 'email'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styles(self)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('phone', 'address', 'city', 'postcode', 'avatar_url', 'delivery_notes')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styles(self)


class CheckoutForm(forms.Form):
    first_name = forms.CharField(max_length=80)
    last_name = forms.CharField(max_length=80)
    email = forms.EmailField(widget=forms.TextInput(attrs={'inputmode': 'email'}))
    phone = forms.CharField(max_length=30)
    address = forms.CharField(max_length=220)
    city = forms.CharField(max_length=80)
    postcode = forms.CharField(max_length=20)
    delivery_notes = forms.CharField(max_length=220, required=False, widget=forms.Textarea(attrs={'rows': 3}))
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styles(self)


def apply_form_styles(form):
    for name, field in form.fields.items():
        if isinstance(field.widget, forms.RadioSelect):
            continue
        label = field.label or name.replace('_', ' ').title()
        field.widget.attrs.setdefault('class', 'form-input')
        field.widget.attrs.setdefault('placeholder', label)
