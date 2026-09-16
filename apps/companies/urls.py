from rest_framework.routers import DefaultRouter

from .views import CompanyViewSet

app_name = "companies"

router = DefaultRouter()
router.register("", CompanyViewSet, basename="company")

urlpatterns = router.urls
