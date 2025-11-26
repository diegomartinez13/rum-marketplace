# store_app/views.py
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required
import logging
from django.http import JsonResponse
from datetime import timedelta
from django.utils import timezone
from django.utils.timesince import timesince
from django.core.mail import send_mail
import secrets  # only if you still want a fallback; see note below

from .forms import PreSignupForm
from .models import (
    User,
    Product,
    ProductCategory,
    ProductImage,
    Service,
    ServiceCategory,
    UserProfile,
    Conversation,
    Message,
)
from .tokens import new_email_token

logger = logging.getLogger(__name__)


def home(request):
    newest_products = get_newest_products(request).get("products", [])
    newest_services = get_newest_services(request).get("services", [])

    products = Product.objects.all()
    services = Service.objects.all()

    products_categories = ProductCategory.objects.all()
    services_categories = ServiceCategory.objects.all()
    user = request.user

    # Calculate total unread messages count for authenticated users
    unread_messages_count = 0
    if user.is_authenticated:
        # Get all conversations where the user is a participant
        user_conversations = Conversation.objects.filter(participants=user)
        # Count all unread messages in these conversations (excluding messages sent by the user)
        unread_messages_count = (
            Message.objects.filter(conversation__in=user_conversations, is_read=False)
            .exclude(sender=user)
            .count()
        )

    context = {
        "newest_products": newest_products,
        "newest_services": newest_services,
        "products": products,
        "products_categories": products_categories,
        "services_categories": services_categories,
        "user": user,
        "services": services,
        "unread_messages_count": unread_messages_count,
    }
    return render(request, "home.html", context)


@login_required
def add_listing(request):
    return render(request, "add_listing.html")


@login_required
def messages_view(request):
    """Display all conversations for the logged-in user"""
    try:
        # Don't use prefetch_related if it might cause issues with missing fields
        # Just get conversations and let Django lazy-load relationships
        conversations = Conversation.objects.filter(participants=request.user)
        logger.info(
            f"Found {conversations.count()} conversations for user {request.user.id}"
        )

        # Add context for each conversation
        conversations_with_context = []
        for conv in conversations:
            try:
                other_participant = conv.get_other_participant(request.user)
                # Skip conversations where other_participant is None (shouldn't happen, but handle gracefully)
                if other_participant is None:
                    logger.warning(
                        f"Conversation {conv.id} has no other participant for user {request.user.id}"
                    )
                    continue

                # Get latest message - handle errors gracefully
                try:
                    latest_message = conv.get_latest_message()
                except Exception as e:
                    logger.warning(
                        f"Error getting latest message for conversation {conv.id}: {str(e)}"
                    )
                    latest_message = None

                # Get unread count - handle errors gracefully
                try:
                    unread_count = (
                        conv.messages.filter(is_read=False)
                        .exclude(sender=request.user)
                        .count()
                    )
                except Exception as e:
                    logger.warning(
                        f"Error getting unread count for conversation {conv.id}: {str(e)}"
                    )
                    unread_count = 0

                # Get unique products and services mentioned in messages
                # Use a set to ensure uniqueness across all databases
                # Wrap in try-except in case fields don't exist yet (migration not run)
                try:
                    mentioned_products_raw = conv.messages.filter(
                        product__isnull=False
                    ).values_list("product", "product__name")
                    mentioned_services_raw = conv.messages.filter(
                        service__isnull=False
                    ).values_list("service", "service__name")

                    # Use dict to ensure uniqueness by ID (keeps last name if duplicates)
                    products_dict = {
                        pid: pname for pid, pname in mentioned_products_raw
                    }
                    services_dict = {
                        sid: sname for sid, sname in mentioned_services_raw
                    }

                    # Convert to lists of dicts for easier template access
                    products_list = [
                        {"id": pid, "name": pname}
                        for pid, pname in products_dict.items()
                    ]
                    services_list = [
                        {"id": sid, "name": sname}
                        for sid, sname in services_dict.items()
                    ]
                except Exception as e:
                    # If fields don't exist yet (migration not run), return empty lists
                    logger.warning(
                        f"Error getting mentioned products/services for conversation {conv.id}: {str(e)}"
                    )
                    products_list = []
                    services_list = []

                conversations_with_context.append(
                    {
                        "conversation": conv,
                        "other_participant": other_participant,
                        "latest_message": latest_message,
                        "unread_count": unread_count,
                        "mentioned_products": products_list,
                        "mentioned_services": services_list,
                    }
                )
            except Exception as e:
                # Log the error but still try to add the conversation with minimal data
                logger.error(
                    f"Error processing conversation {conv.id}: {str(e)}", exc_info=True
                )
                # Try to get at least basic info to show the conversation
                try:
                    other_participant = conv.get_other_participant(request.user)
                    if other_participant:
                        conversations_with_context.append(
                            {
                                "conversation": conv,
                                "other_participant": other_participant,
                                "latest_message": None,
                                "unread_count": 0,
                                "mentioned_products": [],
                                "mentioned_services": [],
                            }
                        )
                except Exception as e2:
                    logger.error(
                        f"Could not add conversation {conv.id} even with minimal data: {str(e2)}"
                    )
                    continue

        context = {
            "conversations": conversations_with_context,
        }
        return render(request, "messages.html", context)
    except Exception as e:
        logger.error(f"Error in messages_view: {str(e)}", exc_info=True)
        # Return empty context on error to prevent 500
        context = {
            "conversations": [],
        }
        return render(request, "messages.html", context)


@login_required
def add_product(request):
    categories = ProductCategory.objects.all()
    if request.method == "POST":
        data = request.POST
        name = data.get("name")
        description = data.get("description")
        price = float(data.get("price"))
        category_id = data.get("category")
        category = get_object_or_404(ProductCategory, id=category_id)
        discount = (
            ((float(data.get("discount")) / 100) * price)
            if data.get("discount")
            else 0.00
        )

        # Handle multiple images (up to 5)
        images = request.FILES.getlist("images")

        # Validate image count
        if not images:
            messages.error(request, "Please upload at least one image.")
            context = {"categories": categories}
            return render(request, "add_product.html", context)

        if len(images) > 5:
            messages.error(request, "You can upload a maximum of 5 images.")
            context = {"categories": categories}
            return render(request, "add_product.html", context)

        # Create product (use first image for backward compatibility)
        product = Product.objects.create(
            name=name,
            description=description,
            price=price,
            category=category,
            discount=discount,
            image=(
                images[0] if images else None
            ),  # First image for backward compatibility
            user_vendor=request.user,
        )

        # Save ALL images to ProductImage model
        for index, img in enumerate(images):
            ProductImage.objects.create(product=product, image=img, order=index)

        messages.success(
            request, f"Product added successfully with {len(images)} image(s)!"
        )
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
        price = float(data.get("price"))
        category_id = data.get("category")
        category = get_object_or_404(ServiceCategory, id=category_id)
        discount = (
            ((float(data.get("discount")) / 100) * price)
            if data.get("discount")
            else 0.00
        )
        image = request.FILES.get("image")

        Service.objects.create(
            name=name,
            description=description,
            price=price,
            category=category,
            discount=discount,
            image=image,
            user_provider=request.user,  # Automatically set logged-in user as provider
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
        services = Service.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    else:
        messages.error(
            request, "Item not founds matching your search. Please try again."
        )
        return redirect("store_app:home")

    return render(
        request,
        "home.html",
        {"products": products, "services": services, "query": query},
    )


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
                if authenticated_user.profile.pending_email_verification:  # type: ignore
                    messages.warning(
                        request,
                        "Please verify your email before logging in. "
                        "Check your inbox for the verification link.",
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
            return render(request, self.template_name, {"form": form}, status=400)

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
            profile = user.profile  # type: ignore
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
            messages.error(
                request, "An error occurred during registration. Please try again."
            )
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
        if (
            profile.email_token_expires_at
            and profile.email_token_expires_at < timezone.now()
        ):
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
        return render(request, "home.html", {"status": "ok"})


def _send_verification_email(request, user, profile):
    """
    Generates a fresh token (60 min expiry) and sends the verification email.
    The email instructs the user to press the button on the page (two-step activation).
    """
    token = new_email_token()
    profile.email_token = token
    profile.email_token_expires_at = timezone.now() + timedelta(minutes=60)
    profile.pending_email_verification = True
    profile.save(
        update_fields=[
            "email_token",
            "email_token_expires_at",
            "pending_email_verification",
        ]
    )

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
            messages.error(
                request, "We didn't find a pending verification for that email."
            )
            return render(request, self.template_name, {"status": "resend_form"})

        try:
            _send_verification_email(request, profile.user, profile)
            messages.success(request, "We sent you a new verification email.")
            return render(request, self.template_name, {"status": "resent"})
        except Exception:
            messages.error(
                request, "Couldn't send the email right now. Try again shortly."
            )
            return render(request, self.template_name, {"status": "resend_form"})


@login_required
def conversation_view(request, conversation_id):
    """Display a specific conversation and handle sending messages"""
    try:
        conversation = get_object_or_404(
            Conversation, id=conversation_id, participants=request.user
        )
    except Http404:
        logger.warning(
            f"Conversation {conversation_id} not found or user {request.user.id} is not a participant"
        )
        return redirect("store_app:messages")
    except Exception as e:
        logger.error(
            f"Error accessing conversation {conversation_id}: {str(e)}", exc_info=True
        )
        return redirect("store_app:messages")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        product_id = request.POST.get("product_id", "").strip()
        service_id = request.POST.get("service_id", "").strip()

        if content:
            # Create new message
            # Handle case where product/service fields might not exist yet (migration not run)
            try:
                message_data = {
                    "conversation": conversation,
                    "sender": request.user,
                    "content": content,
                }
                # Only add product/service if provided and fields exist
                if product_id:
                    try:
                        message_data["product_id"] = int(product_id)
                    except (ValueError, TypeError):
                        pass  # Invalid product_id, skip it
                if service_id:
                    try:
                        message_data["service_id"] = int(service_id)
                    except (ValueError, TypeError):
                        pass  # Invalid service_id, skip it

                # Try to create message with product/service fields
                try:
                    message = Message.objects.create(**message_data)
                except Exception as e:
                    # If fields don't exist in DB, create without them
                    logger.warning(
                        f"Error creating message with product/service fields: {str(e)}"
                    )
                    # Remove product/service from message_data and try again
                    message_data.pop("product_id", None)
                    message_data.pop("service_id", None)
                    message = Message.objects.create(**message_data)

                # Ensure message is saved
                message.save()

                # Update conversation's updated_at timestamp
                conversation.save()

                logger.info(
                    f"Message {message.id} created successfully in conversation {conversation.id}"
                )
            except Exception as e:
                logger.error(f"Error creating message: {str(e)}", exc_info=True)
                if (
                    request.headers.get("X-Requested-With") == "XMLHttpRequest"
                    or request.headers.get("Content-Type")
                    == "application/x-www-form-urlencoded"
                ):
                    from django.http import JsonResponse

                    return JsonResponse(
                        {
                            "success": False,
                            "error": "Failed to send message. Please try again.",
                        }
                    )
                else:
                    messages.error(request, "Failed to send message. Please try again.")
                    return redirect(
                        "store_app:conversation", conversation_id=conversation_id
                    )

            # Check if it's an AJAX request
            if (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.headers.get("Content-Type")
                == "application/x-www-form-urlencoded"
            ):
                from django.http import JsonResponse

                message_data = {
                    "id": message.id,
                    "sender": message.sender.username,
                    "sender_name": message.sender.get_full_name()
                    or message.sender.username,
                    "content": message.content,
                    "timestamp": message.created_at.strftime("%b %d, %Y %I:%M %p"),
                }
                # Add product/service info if present (handle case where fields might not exist)
                try:
                    if hasattr(message, "product") and message.product:
                        message_data["product"] = {
                            "id": message.product.id,
                            "name": message.product.name,
                        }
                    if hasattr(message, "service") and message.service:
                        message_data["service"] = {
                            "id": message.service.id,
                            "name": message.service.name,
                        }
                except Exception as e:
                    # Fields don't exist yet, skip adding product/service info
                    logger.warning(
                        f"Error accessing product/service fields on message: {str(e)}"
                    )
                    pass
                return JsonResponse({"success": True, "message": message_data})
            else:
                messages.success(request, "Message sent!")
                return redirect(
                    "store_app:conversation", conversation_id=conversation_id
                )
        else:
            if (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.headers.get("Content-Type")
                == "application/x-www-form-urlencoded"
            ):
                from django.http import JsonResponse

                return JsonResponse(
                    {"success": False, "error": "Message cannot be empty."}
                )
            else:
                messages.error(request, "Message cannot be empty.")

    # Mark all messages in this conversation as read (except those sent by current user)
    try:
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(
            is_read=True, read_at=timezone.now()
        )
    except Exception as e:
        logger.warning(f"Error marking messages as read: {str(e)}")
        # Continue anyway - this is not critical

    # Get all messages in this conversation
    try:
        messages_list = conversation.messages.all()
        other_participant = conversation.get_other_participant(request.user)

        if not other_participant:
            logger.error(
                f"Conversation {conversation_id} has no other participant for user {request.user.id}"
            )
            messages.error(request, "Invalid conversation.")
            return redirect("store_app:messages")

        # Get all products and services from both participants
        # This allows both buyer and seller to select context for their messages
        available_products = []
        available_services = []

        try:
            if other_participant:
                # Get products/services from both current user and other participant
                try:
                    available_products = Product.objects.filter(
                        Q(user_vendor=request.user) | Q(user_vendor=other_participant)
                    ).order_by("name")
                except Exception as e:
                    logger.warning(f"Error getting available products: {str(e)}")
                    available_products = []
                try:
                    available_services = Service.objects.filter(
                        Q(user_provider=request.user)
                        | Q(user_provider=other_participant)
                    ).order_by("name")
                except Exception as e:
                    logger.warning(f"Error getting available services: {str(e)}")
                    available_services = []
            else:
                # Fallback: just get current user's products/services
                try:
                    available_products = Product.objects.filter(
                        user_vendor=request.user
                    ).order_by("name")
                except Exception as e:
                    logger.warning(f"Error getting available products: {str(e)}")
                    available_products = []
                try:
                    available_services = Service.objects.filter(
                        user_provider=request.user
                    ).order_by("name")
                except Exception as e:
                    logger.warning(f"Error getting available services: {str(e)}")
                    available_services = []
        except Exception as e:
            logger.warning(
                f"Error getting products/services for conversation: {str(e)}"
            )
            # Continue with empty lists - not critical

        context = {
            "conversation": conversation,
            "messages": messages_list,
            "other_participant": other_participant,
            "other_products": available_products,
            "other_services": available_services,
        }
        return render(request, "conversation.html", context)
    except Exception as e:
        logger.error(
            f"Error loading conversation {conversation_id}: {str(e)}", exc_info=True
        )
        # Don't show error message that persists - just redirect silently
        return redirect("store_app:messages")


@login_required
def get_new_messages(request, conversation_id):
    """API endpoint to fetch new messages for a conversation"""
    conversation = get_object_or_404(
        Conversation, id=conversation_id, participants=request.user
    )

    # Get the last message ID from the request (if provided)
    last_message_id = request.GET.get("last_message_id", None)

    # Query for new messages
    if last_message_id:
        try:
            last_message_id = int(last_message_id)
            new_messages = conversation.messages.filter(id__gt=last_message_id).exclude(
                sender=request.user
            )
        except ValueError:
            new_messages = conversation.messages.exclude(sender=request.user)
    else:
        # If no last_message_id provided, get all messages (for initial load)
        new_messages = conversation.messages.exclude(sender=request.user)

    # Mark new messages as read
    new_messages.update(is_read=True, read_at=timezone.now())

    # Serialize messages
    messages_data = []
    for message in new_messages:
        message_data = {
            "id": message.id,
            "sender": message.sender.username,
            "sender_name": message.sender.get_full_name() or message.sender.username,
            "content": message.content,
            "timestamp": message.created_at.strftime("%b %d, %Y %I:%M %p"),
        }
        # Add product/service info if present (handle case where fields might not exist)
        try:
            if hasattr(message, "product") and message.product:
                message_data["product"] = {
                    "id": message.product.id,
                    "name": message.product.name,
                }
            if hasattr(message, "service") and message.service:
                message_data["service"] = {
                    "id": message.service.id,
                    "name": message.service.name,
                }
        except Exception as e:
            # Fields don't exist yet, skip adding product/service info
            logger.warning(
                f"Error accessing product/service fields on message in get_new_messages: {str(e)}"
            )
            pass
        messages_data.append(message_data)

    return JsonResponse({"success": True, "messages": messages_data})


@login_required
def get_unread_messages_count(request):
    """API endpoint to get the total unread messages count for the logged-in user"""
    try:
        user_conversations = Conversation.objects.filter(participants=request.user)
        unread_count = (
            Message.objects.filter(conversation__in=user_conversations, is_read=False)
            .exclude(sender=request.user)
            .count()
        )

        return JsonResponse({"success": True, "unread_count": unread_count})
    except Exception as e:
        logger.error(f"Error in get_unread_messages_count: {str(e)}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": "An error occurred while fetching unread count",
                "unread_count": 0,
            }
        )


@login_required
def get_conversations_update(request):
    """API endpoint to fetch updated conversation data for the messages list"""
    try:
        # Don't use prefetch_related if it might cause issues with missing fields
        conversations = Conversation.objects.filter(participants=request.user)

        conversations_data = []
        for conv in conversations:
            try:
                other_participant = conv.get_other_participant(request.user)
                # Skip conversations where other_participant is None
                if other_participant is None:
                    logger.warning(
                        f"Conversation {conv.id} has no other participant for user {request.user.id}"
                    )
                    continue

                latest_message = conv.get_latest_message()
                unread_count = (
                    conv.messages.filter(is_read=False)
                    .exclude(sender=request.user)
                    .count()
                )

                latest_message_timesince = None
                conversation_timesince = timesince(conv.created_at, timezone.now())
                if latest_message:
                    latest_message_timesince = timesince(
                        latest_message.created_at, timezone.now()
                    )

                # Get unique products and services mentioned in messages
                # Use a dict to ensure uniqueness by ID (keeps last name if duplicates)
                # Wrap in try-except in case fields don't exist yet (migration not run)
                try:
                    mentioned_products_raw = conv.messages.filter(
                        product__isnull=False
                    ).values_list("product", "product__name")
                    mentioned_services_raw = conv.messages.filter(
                        service__isnull=False
                    ).values_list("service", "service__name")

                    # Use dict to ensure uniqueness by ID
                    products_dict = {
                        pid: pname for pid, pname in mentioned_products_raw
                    }
                    services_dict = {
                        sid: sname for sid, sname in mentioned_services_raw
                    }

                    # Convert to lists of dicts
                    products_list = [
                        {"id": pid, "name": pname}
                        for pid, pname in products_dict.items()
                    ]
                    services_list = [
                        {"id": sid, "name": sname}
                        for sid, sname in services_dict.items()
                    ]
                except Exception as e:
                    # If fields don't exist yet (migration not run), return empty lists
                    logger.warning(
                        f"Error getting mentioned products/services for conversation {conv.id} in get_conversations_update: {str(e)}"
                    )
                    products_list = []
                    services_list = []

                conversations_data.append(
                    {
                        "id": conv.id,
                        "other_participant_name": (
                            other_participant.get_full_name()
                            if other_participant
                            else "Unknown"
                        ),
                        "other_participant_username": (
                            other_participant.username
                            if other_participant
                            else "unknown"
                        ),
                        "latest_message": (
                            {
                                "content": (
                                    latest_message.content if latest_message else None
                                ),
                                "timestamp": (
                                    latest_message.created_at.strftime(
                                        "%b %d, %Y %I:%M %p"
                                    )
                                    if latest_message
                                    else None
                                ),
                                "timesince": latest_message_timesince,
                            }
                            if latest_message
                            else None
                        ),
                        "conversation_timesince": conversation_timesince,  # For conversations with no messages
                        "unread_count": unread_count,
                        "updated_at": conv.updated_at.isoformat(),
                        "has_product": conv.product is not None,
                        "has_service": conv.service is not None,
                        "product_name": conv.product.name if conv.product else None,
                        "service_name": conv.service.name if conv.service else None,
                        "mentioned_products": products_list,
                        "mentioned_services": services_list,
                    }
                )
            except Exception as e:
                logger.error(
                    f"Error processing conversation {conv.id} in get_conversations_update: {str(e)}",
                    exc_info=True,
                )
                continue

        return JsonResponse({"success": True, "conversations": conversations_data})
    except Exception as e:
        logger.error(f"Error in get_conversations_update: {str(e)}", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "error": "An error occurred while fetching conversations",
                "conversations": [],
            }
        )


@login_required
def start_conversation(request, user_id):
    """Start a new conversation with another user"""
    other_user = get_object_or_404(User, id=user_id)

    if other_user == request.user:
        messages.error(request, "You cannot start a conversation with yourself.")
        return redirect("store_app:home")

    # Get or create conversation
    conversation, created = Conversation.get_or_create_conversation(
        request.user, other_user
    )

    # Verify conversation exists in database
    if not conversation.id:
        logger.error(
            f"Conversation was not saved properly for users {request.user.id} and {other_user.id}"
        )
        messages.error(request, "Failed to create conversation. Please try again.")
        return redirect("store_app:home")

    # Refresh from DB to ensure we have the latest data
    conversation.refresh_from_db()
    logger.info(
        f"Conversation {conversation.id} {'created' if created else 'retrieved'} for users {request.user.id} and {other_user.id}"
    )

    if not created:
        messages.info(
            request,
            f"You already have a conversation with {other_user.get_full_name() or other_user.username}",
        )

    return redirect("store_app:conversation", conversation_id=conversation.id)


@login_required
def start_conversation_from_listing(request, listing_type, listing_id):
    """Start a conversation from a product or service listing"""
    try:
        if listing_type == "product":
            listing = get_object_or_404(Product, id=listing_id)
            seller = listing.user_vendor
        elif listing_type == "service":
            listing = get_object_or_404(Service, id=listing_id)
            seller = listing.user_provider
        else:
            messages.error(request, "Invalid listing type.")
            return redirect("store_app:home")

        if not seller:
            messages.error(request, "This listing has no seller.")
            return redirect("store_app:home")

        if seller == request.user:
            messages.error(
                request, "You cannot message yourself about your own listing."
            )
            return redirect("store_app:home")

        # Get or create conversation
        conversation, created = Conversation.get_or_create_conversation(
            request.user, seller
        )

        # Ensure conversation is saved
        if not conversation.id:
            conversation.save()

        # Link conversation to the listing
        if listing_type == "product":
            conversation.product = listing
        else:
            conversation.service = listing
        conversation.save()

        # Verify conversation was saved
        conversation.refresh_from_db()
        logger.info(
            f"Conversation {conversation.id} {'created' if created else 'retrieved'} for users {request.user.id} and {seller.id}"
        )

        # Don't show messages - just redirect directly to the conversation
        # This makes the Message Seller button open the chat directly
        return redirect("store_app:conversation", conversation_id=conversation.id)
    except Exception as e:
        logger.error(
            f"Error in start_conversation_from_listing: {str(e)}", exc_info=True
        )
        messages.error(
            request,
            "An error occurred while starting the conversation. Please try again.",
        )
        return redirect("store_app:home")


@login_required
def profile(request):
    """Display and edit user profile"""
    user = request.user
    profile = user.profile  # type: ignore
    products = Product.objects.filter(user_vendor=user)
    services = Service.objects.filter(user_provider=user)

    if request.method == "POST":
        """
        Handle profile updates. In addition to the name and phone number fields,
        update the seller/service flags if present in the submitted form. When
        a checkbox is unchecked it will not appear in `request.POST`, so we
        default to False in those cases.
        """
        # Update the built-in User fields
        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.last_name = request.POST.get("last_name", user.last_name).strip()
        # Update the custom profile fields
        profile.phone_number = request.POST.get(
            "phone_number", profile.phone_number
        ).strip()
        profile.description = request.POST.get(
            "description", profile.description
        ).strip()
        # Booleans: if the checkbox name is in POST, it's True; otherwise False
        profile.is_seller = bool(request.POST.get("is_seller"))
        profile.provides_service = bool(request.POST.get("provides_service"))

        # Handle profile picture deletion
        if request.POST.get("delete_picture") == "true":
            profile.profile_picture.delete(save=False)
            profile.profile_picture = None

        # Handle profile picture upload
        if "profile_picture" in request.FILES:
            profile.profile_picture = request.FILES["profile_picture"]

        # Handle cropped image data (from cropper modal)
        if "cropped_image_data" in request.POST and request.POST["cropped_image_data"]:
            import base64
            from django.core.files.base import ContentFile

            data = request.POST["cropped_image_data"]
            if data.startswith("data:image"):
                # Extract base64 data
                format, imgstr = data.split(";base64,")
                ext = format.split("/")[-1]
                decoded_data = base64.b64decode(imgstr)
                # Create file from decoded data
                filename = f"profile_pic_{user.id}.{ext}"
                profile.profile_picture = ContentFile(decoded_data, filename)

        # Persist changes
        user.save()
        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("store_app:profile")

    context = {
        "user": user,
        "profile": profile,
        "user_products": products,
        "user_services": services,
    }
    return render(request, "profile.html", context)


def update_profile(request, user_id):
    """Update user profile information"""
    user = get_object_or_404(User, id=user_id)
    profile = user.profile  # type: ignore

    if request.method == "POST":
        # Update standard user fields
        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.last_name = request.POST.get("last_name", user.last_name).strip()
        # Update custom profile fields
        profile.phone_number = request.POST.get(
            "phone_number", profile.phone_number
        ).strip()
        profile.description = request.POST.get(
            "description", profile.description
        ).strip()
        profile.is_seller = bool(request.POST.get("is_seller"))
        profile.provides_service = bool(request.POST.get("provides_service"))

        # Handle profile picture deletion
        if request.POST.get("delete_picture") == "true":
            profile.profile_picture.delete(save=False)
            profile.profile_picture = None

        # Handle profile picture upload
        if "profile_picture" in request.FILES:
            profile.profile_picture = request.FILES["profile_picture"]

        # Handle cropped image data (from cropper modal)
        if "cropped_image_data" in request.POST and request.POST["cropped_image_data"]:
            import base64
            from django.core.files.base import ContentFile

            data = request.POST["cropped_image_data"]
            if data.startswith("data:image"):
                # Extract base64 data
                format, imgstr = data.split(";base64,")
                ext = format.split("/")[-1]
                decoded_data = base64.b64decode(imgstr)
                # Create file from decoded data
                filename = f"profile_pic_{user.id}.{ext}"
                profile.profile_picture = ContentFile(decoded_data, filename)

        # Save changes
        user.save()
        profile.save()
        messages.success(request, "Profile updated successfully.")
        # Redirect to the main profile page for the logged-in user
        return redirect("store_app:profile")

    context = {
        "user": user,
        "profile": profile,
    }
    return render(request, "update_profile.html", context)


def product_detail(request, product_id):
    """Display detailed view of a product with image slideshow"""
    product = get_object_or_404(Product, id=product_id)

    # Get all images for this product
    product_images = product.images.all()

    # Get seller information
    seller = product.user_vendor
    seller_name = None
    if seller:
        seller_name = seller.get_full_name() or seller.username

    context = {
        "product": product,
        "product_images": product_images,
        "seller": seller,
        "seller_name": seller_name,
        "user": request.user,
    }
    return render(request, "product_detail.html", context)


def all_products(request):
    """Display all products"""
    products = Product.objects.all()
    context = {
        "products": products,
        "user": request.user,
    }
    return render(request, "all_products.html", context)


def all_services(request):
    """Display all services"""
    services = Service.objects.all()
    context = {
        "services": services,
        "user": request.user,
    }
    return render(request, "all_services.html", context)


def get_newest_products(request):
    """Return the 5 newest products as JSON (for AJAX calls)"""
    newest_products = Product.objects.order_by("-id")[:5]
    return {"products": newest_products}


def get_newest_services(request):
    """Return the 5 newest services as JSON (for AJAX calls)"""
    newest_services = Service.objects.order_by("-id")[:5]
    return {"services": newest_services}
