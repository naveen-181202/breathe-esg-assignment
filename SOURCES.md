# Sources

## SAP fuel and procurement

Researched format: SAP OData/Gateway exports for business objects such as material documents and purchase orders. SAP OData services expose metadata and support JSON/XML-style entity collections, and SAP annotations include unit and precision metadata. I also checked IDoc export discussions and chose not to parse raw IDoc segments for the prototype because they are much less analyst-friendly.

What I learned: realistic SAP exports include technical IDs, plant codes, posting dates, material or service descriptions, quantities with separate units, vendors, currencies, and inconsistent localization. German column names are plausible in SAP-configured environments.

Sample data: `sample_data/sap_fuel_procurement.csv` includes diesel in liters, natural gas in MMBtu, a procurement service line in USD, German headers, and plant codes that require lookup. One row intentionally uses an unknown plant to trigger analyst review.

What would break: client-specific material codes, split account assignments, unusual units, multilingual free text, deleted/reversed documents, and authentication or authorization differences across SAP landscapes.

## Utility electricity

Researched format: utility portal CSV/billing exports and public explanations of electricity bills. Typical bills distinguish energy consumption in kWh, demand in kW, tariffs/rate schedules, service periods, and charges. Billing periods often do not match calendar months.

What I learned: utility data is not just "month + kWh"; the billing period and tariff matter, especially when demand charges or time-of-use pricing exist.

Sample data: `sample_data/utility_electricity.csv` includes meter numbers, billing period start/end dates, kWh, peak kW, tariff, and total charge. One period crosses calendar months and is flagged.

What would break: PDF-only bills, interval data with thousands of rows, multiple meters per facility, estimated reads, solar exports, meter multipliers, and tariff-specific charge calculations.

## Corporate travel

Researched format: Concur-like travel and expense exports/APIs. Travel records commonly include trip/report identifiers, expense types, dates, origins/destinations, travelers, amounts, and sometimes itinerary details. Flight distance is not always provided; airport codes may be the only route data.

What I learned: flight, hotel, and ground transport rows need different activity logic. A single "travel spend" row is not enough for useful emissions review.

Sample data: `sample_data/travel_concur_export.csv` includes flights with airport codes, hotel nights, rail distance, taxi distance, and rental car distance. Flights without explicit distance are estimated for known airport pairs and flagged.

What would break: multi-leg trips, missing airport codes, code shares, refunds, duplicate expense reports, mixed personal/business travel, fare class multipliers, and hotel country-specific factors.

## Web references used

- SAP OData metadata and annotations: https://www.sap.com/protocols/sapdata
- SAP OData extraction concepts: https://help.sap.com/docs/PRODUCT_ID/107a6e8a38b74ede94c833ca3b7b6f51/50f4ee6253134d3cafa25b9444f0c5a9.html
- SAP IDoc export background: https://www.informatikdv.de/how-to-export-an-idoc-to-a-file/
- Concur Travel Allowance API examples: https://preview.developer.concur.com/api-reference/travelallowance/v4.travelallowance-calculationresults-endpoints.html
- Public utility rate/demand charge discussion: https://ww2.arb.ca.gov/sites/default/files/2022-06/ratesanddemand_ADA.pdf
