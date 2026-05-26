from django.db.models import Count, Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .ingestion import ingest_file
from .models import AuditEvent, EmissionActivity, IngestionBatch, SourceConnection, Tenant
from .serializers import (
    AuditEventSerializer,
    EmissionActivitySerializer,
    IngestionBatchSerializer,
    SourceConnectionSerializer,
)


def demo_tenant():
    return Tenant.objects.get(slug="acme-industries")


class SummaryView(APIView):
    def get(self, request):
        tenant = demo_tenant()
        activities = EmissionActivity.objects.filter(tenant=tenant)
        status_counts = dict(activities.values_list("review_status").annotate(count=Count("id")))
        scope_rows = activities.values("scope").annotate(co2e=Sum("co2e_kg"), count=Count("id")).order_by("scope")
        flagged = activities.exclude(quality_flags=[]).count()
        return Response(
            {
                "tenant": tenant.name,
                "total_rows": activities.count(),
                "flagged_rows": flagged,
                "status_counts": status_counts,
                "scope_totals": list(scope_rows),
                "failed_batches": IngestionBatch.objects.filter(tenant=tenant, status=IngestionBatch.FAILED).count(),
            }
        )


class SourceConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SourceConnectionSerializer

    def get_queryset(self):
        return SourceConnection.objects.filter(tenant=demo_tenant()).order_by("source_type")


class IngestionBatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionBatchSerializer

    def get_queryset(self):
        return IngestionBatch.objects.filter(tenant=demo_tenant()).select_related("source")


class EmissionActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmissionActivitySerializer

    def get_queryset(self):
        queryset = EmissionActivity.objects.filter(tenant=demo_tenant()).select_related("facility", "batch")
        review_status = self.request.query_params.get("status")
        source_type = self.request.query_params.get("source_type")
        flagged = self.request.query_params.get("flagged")
        if review_status:
            queryset = queryset.filter(review_status=review_status)
        if source_type:
            queryset = queryset.filter(source_type=source_type)
        if flagged == "true":
            queryset = queryset.exclude(quality_flags=[])
        if flagged == "false":
            queryset = queryset.filter(quality_flags=[])
        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        activity = self.get_object()
        return self._transition(activity, EmissionActivity.APPROVED, "approved", request)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        activity = self.get_object()
        return self._transition(activity, EmissionActivity.REJECTED, "rejected", request)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        activity = self.get_object()
        if activity.review_status != EmissionActivity.APPROVED:
            return Response({"detail": "Only approved rows can be locked."}, status=status.HTTP_400_BAD_REQUEST)
        return self._transition(activity, EmissionActivity.LOCKED, "locked_for_audit", request)

    def _transition(self, activity, next_status, action_name, request):
        previous = activity.review_status
        activity.review_status = next_status
        activity.save(update_fields=["review_status", "updated_at"])
        AuditEvent.objects.create(
            tenant=activity.tenant,
            activity=activity,
            actor=request.data.get("actor", "demo analyst"),
            action=action_name,
            changes={"review_status": {"from": previous, "to": next_status}},
        )
        return Response(EmissionActivitySerializer(activity).data)


class UploadView(APIView):
    def post(self, request):
        source_id = request.data.get("source_id")
        uploaded = request.FILES.get("file")
        if not source_id or not uploaded:
            return Response({"detail": "source_id and file are required."}, status=status.HTTP_400_BAD_REQUEST)
        source = SourceConnection.objects.get(id=source_id, tenant=demo_tenant())
        batch = ingest_file(source, uploaded.file, uploaded.name, actor=request.data.get("actor", "demo analyst"))
        return Response(IngestionBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditEventSerializer

    def get_queryset(self):
        queryset = AuditEvent.objects.filter(tenant=demo_tenant())
        activity_id = self.request.query_params.get("activity_id")
        if activity_id:
            queryset = queryset.filter(Q(activity_id=activity_id) | Q(activity__isnull=True))
        return queryset
