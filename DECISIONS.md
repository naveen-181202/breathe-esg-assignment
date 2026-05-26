# Decisions

## SAP source

I modeled SAP as a CSV export from an OData service rather than a raw IDoc. OData is realistic for enterprise integrations because SAP Gateway exposes named services and metadata, including units and query parameters. For a four-day prototype, a scheduled API pull would be ideal, but a CSV upload that mirrors a flattened OData export is easier to inspect and defend.

Handled subset: fuel material movements and procurement lines with plant, material/service text, posting date, quantity, unit, vendor, currency, and amount. German headers are mapped for common fields such as `Werk`, `Buchungsdatum`, `Menge`, and `Einheit`.

Ignored: full IDoc segment parsing, purchase order lifecycle states, tax handling, account assignment splits, and live SAP authentication.

## Utility source

I chose a facilities-team portal CSV export for electricity. Many utilities provide downloadable usage/billing tables even when APIs are unavailable or procurement of API access is slow. The parser expects account, meter, site, billing period, kWh, optional peak kW, tariff, and total charge.

Handled subset: monthly or irregular billing periods with kWh, demand kW, tariff name, and billing amount. Rows are flagged when billing periods do not align to calendar months or when kWh is unusually high for the site.

Ignored: PDF bill extraction, 15-minute interval data, time-of-use charge decomposition, net metering, and renewable energy certificates.

## Travel source

I modeled travel as a Concur-like expense/travel export CSV. Travel platforms expose trip and expense entities through APIs, but corporate access often starts with exports. Flights may provide airport codes without distance, so the prototype estimates distance for a small airport set and flags the estimate.

Handled subset: flights, hotels, rail, taxi/rideshare, and rental car rows with traveler, trip id, dates, origin/destination, nights, distance, spend, and currency.

Ignored: live OAuth, itinerary reconciliation, fare class, aircraft type, radiative forcing choices, and duplicate expense report handling.

## Analyst workflow

Rows begin as pending. The dashboard highlights failed batches and suspicious rows. Analysts can approve or reject rows, then lock approved rows for audit. I kept review actions row-level because it is the clearest prototype behavior; bulk actions would come next.

## Questions for the PM

- Which emissions factor library should be authoritative for the demo and for production?
- Do analysts need to edit normalized quantities before approval, or should corrections happen by uploading replacement source data?
- Are clients separated only by application auth, or do we need database-level isolation?
- What is the expected auditor export format?
- Which source should be implemented as a real integration first after the prototype?
