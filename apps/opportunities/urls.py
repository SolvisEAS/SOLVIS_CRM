from rest_framework.routers import DefaultRouter

from .views import OpportunityViewSet, PipelineStageViewSet

app_name = "opportunities"

# Router para /api/opportunities/
opportunity_router = DefaultRouter()
opportunity_router.register("", OpportunityViewSet, basename="opportunity")
urlpatterns = opportunity_router.urls

# Router para /api/pipeline-stages/ (recurso raíz aparte, punto 14 del doc)
pipeline_stage_router = DefaultRouter()
pipeline_stage_router.register("", PipelineStageViewSet, basename="pipeline-stage")
pipeline_stage_urlpatterns = pipeline_stage_router.urls
