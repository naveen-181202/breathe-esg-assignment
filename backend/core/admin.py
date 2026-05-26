from django.contrib import admin

from .models import AuditEvent, EmissionActivity, Facility, IngestionBatch, RawSourceRow, SourceConnection, Tenant

admin.site.register(Tenant)
admin.site.register(Facility)
admin.site.register(SourceConnection)
admin.site.register(IngestionBatch)
admin.site.register(RawSourceRow)
admin.site.register(EmissionActivity)
admin.site.register(AuditEvent)
