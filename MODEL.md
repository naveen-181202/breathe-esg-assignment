# Data Model

The central object is `EmissionActivity`: one normalized row that an analyst can review, approve, reject, or leave pending. It is deliberately source-agnostic so SAP fuel rows, utility meter bills, and travel bookings can share one review queue.

## Tenancy

`Tenant` owns all client data. Every `Facility`, `SourceConnection`, `IngestionBatch`, `RawSourceRow`, `EmissionActivity`, and `AuditEvent` links back to a tenant. In a production system this would be enforced through authentication scopes and database-level row security; the prototype keeps the tenant field explicit so the boundary is visible in code.

## Source-of-truth tracking

`SourceConnection` describes the real system or file pattern that produced the data: SAP OData export, utility portal CSV, or travel platform export. `IngestionBatch` records one upload/pull, including who started it, when it ran, status, counts, and parser warnings. `RawSourceRow` stores the untouched row payload and row number. `EmissionActivity` points back to both the batch and the raw row, so an auditor can trace an approved number to the source line that created it.

## Normalized activity

`EmissionActivity` captures:

- `scope`: Scope 1, 2, or 3
- `category`: fuel combustion, purchased electricity, purchased goods/services, business travel, hotel stay, ground transport
- `activity_date`, `period_start`, `period_end`
- `facility` where applicable
- `quantity` and `unit`, after normalization
- `original_quantity` and `original_unit`, before normalization
- `co2e_kg`, using simple demonstrative factors in this prototype
- `currency` and `amount` where procurement/travel spend matters
- `supplier`, `description`, `external_id`
- `review_status`: pending, approved, rejected, or locked
- `quality_flags`: structured warnings such as missing plant lookup, billing-period mismatch, unknown unit, estimated distance, or high variance
- `source_payload`: normalized parser details that are not important enough for first-class columns

Unit normalization is intentionally stored beside original values. Analysts need the clean number, while auditors need to know exactly what arrived.

## Audit Trail

`AuditEvent` records who changed what, when, and why. The app creates events for ingestion, approval, rejection, and locking. Each event has a JSON `changes` payload so field-level edits could be added without changing the audit schema. Approved rows can still be inspected, but locking represents the point where numbers are ready for audit export and should not be silently changed.

## Why this shape

The assignment is about messy ingestion, not carbon methodology. A single normalized review row keeps analyst UX simple while preserving traceability through `RawSourceRow` and `IngestionBatch`. Source-specific details stay in JSON payloads until they prove they deserve stable columns. This is a pragmatic compromise: relational where workflows need filtering and governance, flexible where source formats vary by client.
