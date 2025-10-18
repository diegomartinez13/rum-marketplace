from django.urls import path
from . import views
from django.views.generic import TemplateView
from .views import SignupView, login_view, VerifyEmailView, home
from django.shortcuts import render


app_name = "store_app"

urlpatterns = [
    path("", home, name="home"),
    path("search/", views.search, name="search"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", SignupView.as_view(), name="signup"),
    path("verify/<str:token>/", VerifyEmailView.as_view(), name="verify_email"),
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
]
