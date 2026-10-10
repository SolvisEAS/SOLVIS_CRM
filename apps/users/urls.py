from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MeView, UserViewSet

app_name = "users"

router = DefaultRouter()
router.register("", UserViewSet, basename="user")

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("register/", UserViewSet.as_view({"post": "create"}), name="register"),
] + router.urls
