from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditEventViewSet,
    EmissionActivityViewSet,
    IngestionBatchViewSet,
    SourceConnectionViewSet,
    SummaryView,
    UploadView,
)

router = DefaultRouter()
router.register("sources", SourceConnectionViewSet, basename="sources")
router.register("batches", IngestionBatchViewSet, basename="batches")
router.register("activities", EmissionActivityViewSet, basename="activities")
router.register("audit-events", AuditEventViewSet, basename="audit-events")

urlpatterns = [
    path("", include(router.urls)),
    path("summary/", SummaryView.as_view()),
    path("upload/", UploadView.as_view()),
]
