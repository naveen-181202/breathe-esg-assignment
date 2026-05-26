from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Facility(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="facilities")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    country = models.CharField(max_length=80, blank=True)

    class Meta:
        unique_together = ("tenant", "code")

    def __str__(self):
        return f"{self.code} - {self.name}"


class SourceConnection(models.Model):
    SAP = "sap"
    UTILITY = "utility"
    TRAVEL = "travel"
    SOURCE_TYPES = [
        (SAP, "SAP OData export"),
        (UTILITY, "Utility portal CSV"),
        (TRAVEL, "Travel platform export"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(max_length=24, choices=SOURCE_TYPES)
    name = models.CharField(max_length=160)
    ingestion_mode = models.CharField(max_length=80)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class IngestionBatch(models.Model):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    STATUSES = [(PENDING, "Pending"), (COMPLETE, "Complete"), (FAILED, "Failed")]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="batches")
    source = models.ForeignKey(SourceConnection, on_delete=models.PROTECT, related_name="batches")
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUSES, default=PENDING)
    uploaded_by = models.CharField(max_length=120, default="demo analyst")
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-started_at",)

    def __str__(self):
        return f"{self.source.name} - {self.filename}"


class RawSourceRow(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="raw_rows")
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="raw_rows")
    row_number = models.PositiveIntegerField()
    payload = models.JSONField()
    errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("batch", "row_number")


class EmissionActivity(models.Model):
    SCOPE_1 = "scope_1"
    SCOPE_2 = "scope_2"
    SCOPE_3 = "scope_3"
    SCOPES = [(SCOPE_1, "Scope 1"), (SCOPE_2, "Scope 2"), (SCOPE_3, "Scope 3")]

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    LOCKED = "locked"
    REVIEW_STATUSES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (LOCKED, "Locked"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="activities")
    batch = models.ForeignKey(IngestionBatch, on_delete=models.PROTECT, related_name="activities")
    raw_row = models.OneToOneField(RawSourceRow, on_delete=models.PROTECT, related_name="activity")
    facility = models.ForeignKey(Facility, null=True, blank=True, on_delete=models.SET_NULL)
    source_type = models.CharField(max_length=24)
    external_id = models.CharField(max_length=120, blank=True)
    scope = models.CharField(max_length=16, choices=SCOPES)
    category = models.CharField(max_length=80)
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    original_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    original_unit = models.CharField(max_length=40, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    unit = models.CharField(max_length=40, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, blank=True)
    co2e_kg = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    review_status = models.CharField(max_length=16, choices=REVIEW_STATUSES, default=PENDING)
    quality_flags = models.JSONField(default=list, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["tenant", "review_status"]),
            models.Index(fields=["tenant", "scope"]),
            models.Index(fields=["source_type"]),
        ]

    def __str__(self):
        return f"{self.scope} {self.category} {self.quantity} {self.unit}"


class AuditEvent(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="audit_events")
    activity = models.ForeignKey(
        EmissionActivity, null=True, blank=True, on_delete=models.CASCADE, related_name="audit_events"
    )
    batch = models.ForeignKey(
        IngestionBatch, null=True, blank=True, on_delete=models.CASCADE, related_name="audit_events"
    )
    actor = models.CharField(max_length=120)
    action = models.CharField(max_length=80)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
