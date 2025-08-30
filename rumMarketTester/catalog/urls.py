from django.urls import path
from . import views
app_name = "catalog"
urlpatterns = [
    path("", views.home, name="home"),
    path("api/listings/<int:pk>/", views.listing_detail_json, name="listing_detail_json"),
]
