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
    PendingSignup,
    Product,
    ProductCategory,
    Service,
    ServiceCategory,
)
from .tokens import generate_signup_token

logger = logging.getLogger(__name__)


def home(request):
    products = Product.objects.all()
    return render(request, "home.html", {"products": products})


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
        seller = request.user if request.user.is_authenticated and request.user.is_seller else None

        Product.objects.create(
            name=name,
            description=description,
            price=price,
            category=category,
            discounted_price=discount,
            seller=seller,
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
        seller = request.user if request.user.is_authenticated and request.user.is_seller else None

        Service.objects.create(
            name=name,
            description=description,
            price=price,
            category=category,
            discounted_price=discount,
            seller=seller,
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
        form = PreSignupForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = PreSignupForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        cd = form.cleaned_data

        # Build PendingSignup instance (mirror the user data)
        pending = PendingSignup.from_raw(
            username=cd["username"],
            first_name=cd["first_name"],
            last_name=cd["last_name"],
            email=cd["email"],
            raw_password=cd["password"],
            is_seller=cd.get("is_seller", False),
            provides_service=cd.get("provides_service", False),
            phone_number=cd.get("phone_number", ""),
            is_admin=False,  # never from public form
        )

        # Set token & expiry (ensure from_raw set created_at)
        pending.token = generate_signup_token()
        # If from_raw already set expires_at, keep it; else set now+60min
        if not pending.expires_at:
            pending.expires_at = timezone.now() + timedelta(minutes=60)

        pending.save()

        # Build verification link (absolute URL)
        verify_url = request.build_absolute_uri(
            reverse("verify-email", kwargs={"token": pending.token})
        )

        # Send verification email
        subject = "Verify your RUM Marketplace account"
        body = (
            f"Hola {pending.first_name},\n\n"
            "Confirma tu cuenta para completar tu registro en RUM Marketplace.\n\n"
            f"Verificar ahora: {verify_url}\n\n"
            "Este enlace expira en 60 minutos.\n\n"
            "Si no fuiste tu, ignora este correo."
        )

        # Choose either send_mail or EmailMessage (both shown, use one)
        try:
            if getattr(settings, "USE_EMAILMESSAGE", False):
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    to=[pending.email],
                )
                email.send(fail_silently=False)
            else:
                send_mail(
                    subject,
                    body,
                    getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    [pending.email],
                    fail_silently=False,
                )
        except Exception as e:
            # If email fails, cleanup the pending row to avoid dead tokens
            pending.delete()
            messages.error(
                request,
                "No se pudo enviar el correo de verificacion. Intenta nuevamente.",
            )
            return render(request, self.template_name, {"form": form})

        messages.success(
            request,
            "Te enviamos un correo para verificar tu cuenta (vigente por 60 minutos).",
        )
        return redirect("signup-thanks")


def signup_thanks(request):
    return render(request, "signup_thanks.html")


class VerifyEmailView(View):
    template_name = "verify_result.html"

    def get(self, request, token):
        # Find pending record by token
        pending = PendingSignup.objects.filter(token=token).first()
        if not pending:
            return render(
                request,
                self.template_name,
                {"status": "error", "message": "Token inv�lido."},
            )

        # Check expiration
        if pending.is_expired():
            # Optionally: offer a re-send flow here
            # pending.delete()  # Keep or delete; your choice
            return render(
                request,
                self.template_name,
                {
                    "status": "expired",
                    "message": "El enlace de verificaci�n ha expirado. Solicita uno nuevo.",
                },
            )

        # If there's already a real user with this email/username, block
        if User.objects.filter(email__iexact=pending.email).exists():
            pending.delete()
            return render(
                request,
                self.template_name,
                {
                    "status": "error",
                    "message": "Esta cuenta ya fue activada o el email ya está en uso.",
                },
            )
        if User.objects.filter(username__iexact=pending.username).exists():
            pending.delete()
            return render(
                request,
                self.template_name,
                {
                    "status": "error",
                    "message": "Este nombre de usuario ya est� en uso.",
                },
            )

        # Create the real user
        user = User.objects.create(
            is_admin=pending.is_admin,
            first_name=pending.first_name,
            last_name=pending.last_name,
            username=pending.username,
            email=pending.email.lower(),
            password=pending.password_hash,  # already hashed in from_raw
            is_seller=pending.is_seller,
            provides_service=pending.provides_service,
            phone_number=pending.phone_number,
        )

        # Remove the pending row
        pending.delete()

        return render(
            request,
            self.template_name,
            {
                "status": "ok",
                "message": "¡Cuenta verificada! Ya puedes iniciar sesión.",
                "username": user.username,
            },
        )
