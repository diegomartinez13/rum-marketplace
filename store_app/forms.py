from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from .models import User, PendingSignup

ALLOWED_DOMAIN = "upr.edu"


class PreSignupForm(forms.Form):
    # Core identity
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=100)
    username = forms.CharField(max_length=150)

    # Contact
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20, required=False)

    # Roles (public toggles; is_admin is NOT exposed here)
    is_seller = forms.BooleanField(required=False)
    provides_service = forms.BooleanField(required=False)

    # Auth
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )

    # ---------- Field-level validation ----------

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        # Also block active, non-expired pending signups with the same username
        if PendingSignup.objects.filter(
            username__iexact=username, expires_at__gt=timezone.now()
        ).exists():
            raise ValidationError("A pending signup for this username already exists.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email.endswith("@" + ALLOWED_DOMAIN):
            raise ValidationError(f"You must use a @{ALLOWED_DOMAIN} email to register.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        # Block duplicates when a valid (non-expired) pending exists
        if PendingSignup.objects.filter(
            email__iexact=email, expires_at__gt=timezone.now()
        ).exists():
            raise ValidationError(
                "There is already a pending signup for this email. Check your inbox."
            )
        return email

    def clean_password(self):
        # Run Django’s password validators (settings.py -> AUTH_PASSWORD_VALIDATORS)
        pwd = self.cleaned_data.get("password")
        if pwd:
            validate_password(pwd)
        return pwd

    # ---------- Cross-field validation ----------
    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password"), cleaned.get("confirm_password")
        if p1 and p2 and p1 != p2:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned

