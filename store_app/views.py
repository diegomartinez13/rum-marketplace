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


def add_listing(request):
    return render(request, "add_listing.html")


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
            if request.user.is_authenticated and request.user.is_seller
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
        return redirect("home")

    context = {"categories": categories}
    return render(request, "add_product.html", context)


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
            if request.user.is_authenticated and request.user.is_seller
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
        return redirect("home")

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
    # NOTE: This assumes a Django-auth User model (with username/password).
    # Your current custom User model is not wired to Django auth, so this is likely placeholder.
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            # If you keep a custom user table, you'll need a custom auth backend.
            # This line will fail if your custom User has no username field.
            user_obj = User.objects.get(email=email)
            user = authenticate(
                request,
                username=getattr(user_obj, "username", email),
                password=password,
            )
            if user is not None:
                login(request, user)
                messages.success(request, "Successfully logged in!")
                return redirect("home")
            else:
                messages.error(request, "Invalid email or password.")
        except User.DoesNotExist:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")


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

        user = User(
            username=cd["username"].lower(),
            first_name=cd["first_name"].strip(),
            last_name=cd["last_name"].strip(),
            email=cd["email"].lower(),
            phone_number=cd.get("phone_number", "").strip(),
            is_seller=cd.get("is_seller", False),
            provides_service=cd.get("provides_service", False),
            pendingemail=True,
            email_token=token,
            email_token_expires_at=expires,
        )
        user.set_password_raw(cd["password"])
        user.save()

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


class VerifyEmailView(View):
    template_name = "verify_result.html"

    def get(self, request, token):
        user = User.objects.filter(email_token=token).first()
        if not user:
            messages.error(request, "Invalid or used verification link.")
            return render(request, self.template_name, {"status": "error"})

        if user.email_token_expires_at and user.email_token_expires_at < timezone.now():
            messages.error(request, "This verification link has expired.")
            return render(request, self.template_name, {"status": "expired"})

        user.mark_verified()
        messages.success(request, "Email verified. You can now use all features.")
        return render(request, self.template_name, {"status": "ok"})
