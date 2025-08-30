from django.urls import path
from . import views
app_name = 'accounts'
urlpatterns = [
    path('login-json/', views.login_json, name='login_json'),
    path('signup-json/', views.signup_json, name='signup_json'),
    path('logout-json/', views.logout_json, name='logout_json'),
]
