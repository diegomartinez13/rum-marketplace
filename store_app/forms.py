from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User


class PreSignupForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField(max_length=100)
    phone_number = forms.CharField(max_length=20, required=False)
    is_seller = forms.BooleanField(required=False)
    provides_service = forms.BooleanField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email.endswith("@upr.edu"):
            raise ValidationError("Use your @upr.edu email.")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already registered.")
        return email

    def clean_username(self):
        u = self.cleaned_data["username"].strip().lower()
        if User.objects.filter(username=u).exists():
            raise ValidationError("Username already taken.")
        return u

    def clean(self):
        cd = super().clean()
        if cd.get("password") != cd.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        else:
            validate_password(cd.get("password"))  # type: ignore
        return cd
