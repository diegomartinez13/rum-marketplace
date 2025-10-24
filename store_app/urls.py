from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.shortcuts import render
from . import views

app_name = "store_app"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("verify/<str:token>/", views.VerifyEmailView.as_view(), name="verify_email"),
    path("verify/resend/", views.ResendVerificationView.as_view(), name="resend_verification"),
    path(
        "verify-email/",
        lambda r: render(r, "registration/email_verification_sent.html"),
        name="email_verification_sent",
    ),
    path("add-listing/", views.add_listing, name="add-listing"),
    path("messages/", views.messages_view, name="messages"),
    path("conversation/<int:conversation_id>/", views.conversation_view, name="conversation"),
    path("start-conversation/<int:user_id>/", views.start_conversation, name="start_conversation"),
    path("message-listing/<str:listing_type>/<int:listing_id>/", views.start_conversation_from_listing, name="message_listing"),
    path("add-product/", views.add_product, name="add-product"),
    path("add-service/", views.add_service, name="add-service"),
    path("profile/", views.profile, name="profile"),
    path("update-profile/<int:user_id>/", views.update_profile, name="update_profile"),
    # path("product/<int:product_id>/", views.product_detail, name="product_detail"),
    # path("service/<int:service_id>/", views.service_detail, name="service_detail"),
    path("all-products/", views.all_products, name="all_products"),
    path("all-services/", views.all_services, name="all_services"),
]
