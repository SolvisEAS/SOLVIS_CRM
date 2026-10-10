from rest_framework.routers import DefaultRouter

from .views import TenantBackofficeViewSet, UserBackofficeViewSet

router = DefaultRouter()
router.register("tenants", TenantBackofficeViewSet, basename="backoffice-tenant")
router.register("users", UserBackofficeViewSet, basename="backoffice-user")
urlpatterns = router.urls
