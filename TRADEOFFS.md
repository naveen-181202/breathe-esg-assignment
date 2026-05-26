# Tradeoffs

1. I did not build authentication or role-based access control. The schema is tenant-aware and audit-aware, but a prototype login flow would consume time without proving the ingestion model. In production, tenant membership and analyst/auditor roles would be mandatory.

2. I did not build live SAP, utility, or Concur API connectors. The assignment asks for realistic shapes, and file ingestion lets reviewers inspect the sample data and parser behavior. Production would add scheduled connector jobs behind the same `SourceConnection` and `IngestionBatch` tables.

3. I did not implement a full emissions factor engine. The prototype uses transparent fixed factors so review behavior is testable. Production should version factor sets by geography, fuel type, travel mode, date, and methodology, then store the factor version used on each row.
