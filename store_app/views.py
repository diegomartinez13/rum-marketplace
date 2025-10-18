# store_app/views.py
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.contrib.auth.decorators import login_required
import logging

from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
import secrets  # only if you still want a fallback; see note below

from .forms import PreSignupForm
from .models import (
    User,
    Product,
    ProductCategory,
    Service,
    ServiceCategory,
    UserProfile,
)
from .tokens import new_email_token

logger = logging.getLogger(__name__)


def home(request):
    products = Product.objects.all()
    categories = ProductCategory.objects.all()
    user = request.user

    context = {
        "products": products,
        "categories": categories,
        "user": user,
    }
    return render(request, "home.html", context)

@login_required
def add_listing(request):
    return render(request, "add_listing.html")

def messages_view(request):
    return render(request, "messages.html")

@login_required
def add_product(request):
    categories = ProductCategory.objects.all()
    if request.method == "POST":
        data = request.POST
        name = data.get("name")
        description = data.get("description")
        price = data.get("price")
        category_id = data.get("category")
        category = get_object_or_404(ProductCategory, id=category_id)
        discount = data.get("discount")
        seller = (
            request.user
            if request.user.is_authenticated and request.user.profile.is_seller
            else messages.error(request, "You must be a seller to add a product.")
            and redirect("store_app:login")
        )

        Product.objects.create(
            name=name,
            description=description,
            price=price,
            category=category,
            discounted_price=discount,
            user_vendor=seller,
        )
        messages.success(request, "Product added successfully!")
        return redirect("store_app:home")

    context = {"categories": categories}
    return render(request, "add_product.html", context)


@login_required
def add_service(request):
    categories = ServiceCategory.objects.all()
    if request.method == "POST":
        data = request.POST
        name = data.get("name")
        description = data.get("description")
        price = data.get("price")
        category_id = data.get("category")
        category = get_object_or_404(ServiceCategory, id=category_id)
        discount = data.get("discount")
        seller = (
            request.user
            if request.user.is_authenticated and request.user.profile.is_seller
            else messages.error(request, "You must be a seller to add a product.")
            and redirect("store_app:login")
        )

        Service.objects.create(
            name=name,
            description=description,
            price=price,
            category=category,
            discounted_price=discount,
            user_provider=seller,
        )
        messages.success(request, "Service added successfully!")
        return redirect("store_app:home")

    context = {"categories": categories}
    return render(request, "add_service.html", context)


def create_category(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        category_type = request.POST.get("category_type")

        if category_type == "product":
            ProductCategory.objects.create(name=name, description=description)
            messages.success(request, "Product category created successfully!")
        elif category_type == "service":
            ServiceCategory.objects.create(name=name, description=description)
            messages.success(request, "Service category created successfully!")
        else:
            messages.error(request, "Invalid category type.")

        return redirect("add-listing")

    return render(request, "create_category.html")


def search(request):
    query = request.GET.get("q", "")
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    else:
        products = Product.objects.all()

    return render(request, "home.html", {"products": products, "query": query})


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        if not email or not password:
            messages.error(request, "Please provide both email and password.")
            return redirect("store_app:login")

        try:
            # Find user by email (since we're using email for login)
            user = User.objects.get(email=email.lower())
            
            # Authenticate using username (Django's default) or custom backend
            authenticated_user = authenticate(
                request,
                username=user.username,  # Use the username for authentication
                password=password,
            )
            
            if authenticated_user is not None:
                # Check if user's email is verified (your business logic)
                if authenticated_user.profile.pending_email_verification: # type: ignore
                    messages.warning(
                        request, 
                        "Please verify your email before logging in. "
                        "Check your inbox for the verification link."
                    )
                    return redirect("store_app:home")
                
                # Log the user in
                login(request, authenticated_user)
                
                # Handle "remember me" functionality
                if not remember_me:
                    # Set session to expire when browser closes
                    request.session.set_expiry(0)
                
                messages.success(request, f"Welcome back, {user.first_name}!")
                
                return redirect("store_app:home")
            else:
                messages.error(request, "Invalid email or password.")
                
        except User.DoesNotExist:
            # Don't reveal whether email exists for security
            messages.error(request, "Invalid email or password.")

        # redirect to home if logged in successfully
        return redirect("store_app:home")
    
    # GET request - show login form
    return render(request, "login.html")

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("store_app:home")


class SignupView(View):
    template_name = "signup.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PreSignupForm()})

    def post(self, request):
        form = PreSignupForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        cd = form.cleaned_data
        token, expires = new_email_token(hours_valid=1)

        try:
            # Create Django User (for authentication)
            user = User.objects.create_user(
                username=cd["username"].lower(),
                email=cd["email"].lower(),
                password=cd["password"],  # Django handles hashing automatically
                first_name=cd["first_name"].strip(),
                last_name=cd["last_name"].strip(),
            )
            
            # The UserProfile is automatically created via signal
            # Now update the profile with your custom fields
            profile = user.profile # type: ignore
            profile.phone_number = cd.get("phone_number", "").strip()
            profile.is_seller = cd.get("is_seller", False)
            profile.provides_service = cd.get("provides_service", False)
            profile.pending_email_verification = True
            profile.email_token = token
            profile.email_token_expires_at = expires
            profile.save()

            # Send verification email
            activate_url = request.build_absolute_uri(
                reverse("store_app:verify_email", kwargs={"token": token})
            )
            subject = "Verify your RUM Marketplace email"
            body = f"Hi {user.first_name},\n\nConfirm your email:\n{activate_url}\n\nThis link expires in 1 hour."
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
            except Exception:
                pass  # don't block UX on email errors

            return redirect("store_app:email_verification_sent")

        except Exception as e:
            # Handle unique constraint violations (username/email already exists)
            messages.error(request, "An error occurred during registration. Please try again.")
            return render(request, self.template_name, {"form": form})


class VerifyEmailView(View):
    """
    Two-step email verification:
    - GET  /accounts/verify/<token>/  -> show confirmation page with a button
    - POST /accounts/verify/<token>/  -> re-check token + expiry, then activate
    """
    
    confirm_template = "activation_confirm.html"
    result_template = "verify_result.html"

    def _get_profile_for_token(self, token):
        from django.utils import timezone
        try:
            profile = UserProfile.objects.select_related("user").get(
                email_token=token,
                pending_email_verification=True,
            )
        except UserProfile.DoesNotExist:
            return None, "invalid"

        # Expiration check
        if profile.email_token_expires_at and profile.email_token_expires_at < timezone.now():
            return None, "expired"

        return profile, "ok"

    def get(self, request, token):
        # Show the confirmation page only (do NOT activate here)
        profile, status = self._get_profile_for_token(token)
        if status != "ok":
            # Render a generic result page the app already uses
            return render(request, self.result_template, {"status": status})

        return render(
            request,
            self.confirm_template,
            {
                "user": profile.user,
                "token": token,  # included as hidden field in the form
            },
        )

    def post(self, request, token):
        # Only a human click (POST) can activate the account
        profile, status = self._get_profile_for_token(token)
        if status != "ok":
            return render(request, self.result_template, {"status": status})

        # Re-check that the token still matches (defense-in-depth)
        if profile.email_token != token or not profile.pending_email_verification:
            return render(request, self.result_template, {"status": "invalid"})

        # Mark verified
        profile.mark_verified()

        messages.success(request, "Email verified. You can now use all features.")
        return render(request, self.result_template, {"status": "ok"})

def _send_verification_email(request, user, profile):
  """
  Generates a fresh token (60 min expiry) and sends the verification email.
  The email instructs the user to press the button on the page (two-step activation).
  """
  token = new_email_token()
  profile.email_token = token
  profile.email_token_expires_at = timezone.now() + timedelta(minutes=60)
  profile.pending_email_verification = True
  profile.save(update_fields=["email_token", "email_token_expires_at", "pending_email_verification"])

  activate_url = request.build_absolute_uri(
      reverse("store_app:verify_email", kwargs={"token": token})
  )
  ctx = {"username": user.username, "activate_url": activate_url}

  html_body = render_to_string("emails/verify_email.html", ctx)
  email = EmailMessage(
      subject="Verify your RUM Marketplace email",
      body=html_body,
      from_email=settings.DEFAULT_FROM_EMAIL,
      to=[user.email],
  )
  email.content_subtype = "html"
  email.send(fail_silently=False)

class ResendVerificationView(View):
    template_name = "verify_result.html"

    def getResendVerifiaction(self, request):
        # show the small form
        return render(request, self.template_name, {"status": "resend_form"})

    def createResendVerification(self, request):
        email = (request.POST.get("email") or "").strip().lower()
        if not email:
            messages.error(request, "Please enter your email.")
            return render(request, self.template_name, {"status": "resend_form"})

        # look for a user profile with pending verification
        profile = (
            UserProfile.objects.select_related("user")
            .filter(
                Q(user__email__iexact=email),
                Q(pending_email_verification=True),
            )
            .first()
        )
        if not profile:
            messages.error(request, "We didn't find a pending verification for that email.")
            return render(request, self.template_name, {"status": "resend_form"})

        try:
            _send_verification_email(request, profile.user, profile)
            messages.success(request, "We sent you a new verification email.")
            return render(request, self.template_name, {"status": "resent"})
        except Exception:
            messages.error(request, "Couldn't send the email right now. Try again shortly.")
            return render(request, self.template_name, {"status": "resend_form"})
