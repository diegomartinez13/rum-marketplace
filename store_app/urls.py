from django.urls import path
from . import views
from django.views.generic import TemplateView
from .views import SignupView, login_view, VerifyEmailView, signup_thanks

urlpatterns = [
    path('', views.home, name="home"),
    path('search/', views.search, name="search"),
    path('login/', views.login_view, name="login"),
    path('logout/', views.logout_view, name="logout"),
    path("signup/", SignupView.as_view(), name="signup"),
    path("signup/thanks/", signup_thanks, name="signup-thanks"),
    path("verify/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
]
