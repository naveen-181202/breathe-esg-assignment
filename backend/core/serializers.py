from rest_framework import serializers

from .models import AuditEvent, EmissionActivity, Facility, IngestionBatch, SourceConnection, Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug"]


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ["id", "code", "name", "country"]


class SourceConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceConnection
        fields = ["id", "source_type", "name", "ingestion_mode", "details"]


class IngestionBatchSerializer(serializers.ModelSerializer):
    source = SourceConnectionSerializer(read_only=True)

    class Meta:
        model = IngestionBatch
        fields = [
            "id",
            "source",
            "filename",
            "status",
            "uploaded_by",
            "started_at",
            "completed_at",
            "row_count",
            "failed_count",
            "warning_count",
            "notes",
        ]


class EmissionActivitySerializer(serializers.ModelSerializer):
    facility = FacilitySerializer(read_only=True)
    batch_id = serializers.IntegerField(source="batch.id", read_only=True)

    class Meta:
        model = EmissionActivity
        fields = [
            "id",
            "batch_id",
            "facility",
            "source_type",
            "external_id",
            "scope",
            "category",
            "activity_date",
            "period_start",
            "period_end",
            "supplier",
            "description",
            "original_quantity",
            "original_unit",
            "quantity",
            "unit",
            "amount",
            "currency",
            "co2e_kg",
            "review_status",
            "quality_flags",
            "source_payload",
            "created_at",
        ]


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "activity_id", "batch_id", "actor", "action", "changes", "created_at"]
