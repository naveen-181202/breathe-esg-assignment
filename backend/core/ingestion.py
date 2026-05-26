import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper

from django.db import transaction
from django.utils import timezone

from .models import AuditEvent, EmissionActivity, Facility, IngestionBatch, RawSourceRow, SourceConnection


SAP_HEADER_MAP = {
    "Werk": "plant_code",
    "Plant": "plant_code",
    "Buchungsdatum": "posting_date",
    "Posting Date": "posting_date",
    "Material": "material",
    "Material Text": "material_text",
    "Kurztext": "material_text",
    "Menge": "quantity",
    "Quantity": "quantity",
    "Einheit": "unit",
    "Unit": "unit",
    "Lieferant": "supplier",
    "Vendor": "supplier",
    "Betrag": "amount",
    "Amount": "amount",
    "Wahrung": "currency",
    "Currency": "currency",
    "Beleg": "document_id",
    "Document": "document_id",
}

UNIT_ALIASES = {
    "l": ("L", Decimal("1")),
    "liter": ("L", Decimal("1")),
    "litre": ("L", Decimal("1")),
    "gal": ("L", Decimal("3.78541")),
    "gallon": ("L", Decimal("3.78541")),
    "mmbtu": ("MMBtu", Decimal("1")),
    "therm": ("MMBtu", Decimal("0.1")),
    "kwh": ("kWh", Decimal("1")),
    "mwh": ("kWh", Decimal("1000")),
    "km": ("km", Decimal("1")),
    "mi": ("km", Decimal("1.60934")),
    "mile": ("km", Decimal("1.60934")),
    "nights": ("night", Decimal("1")),
    "night": ("night", Decimal("1")),
}

AIRPORT_DISTANCE_KM = {
    ("BLR", "DEL"): Decimal("1704"),
    ("DEL", "LHR"): Decimal("6730"),
    ("BOM", "DXB"): Decimal("1925"),
    ("SFO", "JFK"): Decimal("4160"),
}

EMISSION_FACTORS = {
    "diesel_l": Decimal("2.68"),
    "natural_gas_mmbtu": Decimal("53.06"),
    "grid_electricity_kwh": Decimal("0.716"),
    "procurement_usd": Decimal("0.35"),
    "flight_km": Decimal("0.158"),
    "rail_km": Decimal("0.041"),
    "taxi_km": Decimal("0.171"),
    "rental_car_km": Decimal("0.192"),
    "hotel_night": Decimal("19.0"),
}


@dataclass
class ParsedActivity:
    fields: dict
    flags: list[str]
    errors: list[str]


def ingest_file(source: SourceConnection, uploaded_file, filename: str, actor: str = "demo analyst"):
    batch = IngestionBatch.objects.create(
        tenant=source.tenant,
        source=source,
        filename=filename,
        uploaded_by=actor,
    )
    wrapper = TextIOWrapper(uploaded_file, encoding="utf-8-sig")
    rows = list(csv.DictReader(wrapper))

    parser = {
        SourceConnection.SAP: parse_sap_row,
        SourceConnection.UTILITY: parse_utility_row,
        SourceConnection.TRAVEL: parse_travel_row,
    }[source.source_type]

    failed = 0
    warnings = 0
    with transaction.atomic():
        for index, row in enumerate(rows, start=2):
            raw = RawSourceRow.objects.create(
                tenant=source.tenant,
                batch=batch,
                row_number=index,
                payload=row,
            )
            parsed = parser(source.tenant, row)
            raw.errors = parsed.errors
            raw.save(update_fields=["errors"])
            if parsed.errors:
                failed += 1
                continue
            warnings += len(parsed.flags)
            activity = EmissionActivity.objects.create(
                tenant=source.tenant,
                batch=batch,
                raw_row=raw,
                source_type=source.source_type,
                quality_flags=parsed.flags,
                **parsed.fields,
            )
            AuditEvent.objects.create(
                tenant=source.tenant,
                activity=activity,
                batch=batch,
                actor=actor,
                action="ingested",
                changes={"source_type": source.source_type, "flags": parsed.flags},
            )

        batch.row_count = len(rows)
        batch.failed_count = failed
        batch.warning_count = warnings
        batch.status = IngestionBatch.FAILED if failed == len(rows) and rows else IngestionBatch.COMPLETE
        batch.completed_at = timezone.now()
        batch.save()
        AuditEvent.objects.create(
            tenant=source.tenant,
            batch=batch,
            actor=actor,
            action="batch_completed",
            changes={"rows": len(rows), "failed": failed, "warnings": warnings},
        )
    return batch


def parse_sap_row(tenant, row):
    normalized = {SAP_HEADER_MAP.get(k, k): v for k, v in row.items()}
    flags = []
    errors = []
    plant_code = text(normalized.get("plant_code"))
    facility = Facility.objects.filter(tenant=tenant, code=plant_code).first()
    if not facility:
        flags.append(f"Unknown SAP plant code: {plant_code or 'blank'}")

    quantity = decimal_or_none(normalized.get("quantity"))
    original_unit = text(normalized.get("unit"))
    unit, converted = normalize_unit(quantity, original_unit, errors)
    material_text = text(normalized.get("material_text") or normalized.get("material"))
    amount = decimal_or_none(normalized.get("amount"))
    category = "fuel combustion" if looks_like_fuel(material_text) else "purchased goods/services"
    scope = EmissionActivity.SCOPE_1 if category == "fuel combustion" else EmissionActivity.SCOPE_3
    co2e = estimate_sap_emissions(material_text, unit, converted, amount)
    if co2e is None:
        flags.append("No matching demonstrative emissions factor")

    return ParsedActivity(
        fields={
            "facility": facility,
            "external_id": text(normalized.get("document_id")),
            "scope": scope,
            "category": category,
            "activity_date": parse_date(normalized.get("posting_date"), errors),
            "supplier": text(normalized.get("supplier")),
            "description": material_text,
            "original_quantity": quantity,
            "original_unit": original_unit,
            "quantity": converted,
            "unit": unit,
            "amount": amount,
            "currency": text(normalized.get("currency")),
            "co2e_kg": co2e,
            "source_payload": {"normalized_headers": normalized},
        },
        flags=flags,
        errors=errors,
    )


def parse_utility_row(tenant, row):
    flags = []
    errors = []
    facility = Facility.objects.filter(tenant=tenant, code=text(row.get("site_code"))).first()
    if not facility:
        flags.append(f"Unknown site code: {text(row.get('site_code')) or 'blank'}")
    start = parse_date(row.get("period_start"), errors)
    end = parse_date(row.get("period_end"), errors)
    kwh = decimal_or_none(row.get("kwh"))
    unit, quantity = normalize_unit(kwh, "kWh", errors)
    if start and end and (start.day != 1 or end.day not in (28, 29, 30, 31)):
        flags.append("Billing period does not align to a calendar month")
    if quantity and quantity > Decimal("200000"):
        flags.append("High electricity usage for a single bill")

    return ParsedActivity(
        fields={
            "facility": facility,
            "external_id": text(row.get("bill_id") or row.get("meter_number")),
            "scope": EmissionActivity.SCOPE_2,
            "category": "purchased electricity",
            "period_start": start,
            "period_end": end,
            "supplier": text(row.get("utility")),
            "description": f"Meter {text(row.get('meter_number'))} {text(row.get('tariff'))}",
            "original_quantity": kwh,
            "original_unit": "kWh",
            "quantity": quantity,
            "unit": unit,
            "amount": decimal_or_none(row.get("total_charge")),
            "currency": text(row.get("currency")),
            "co2e_kg": quantity * EMISSION_FACTORS["grid_electricity_kwh"] if quantity is not None else None,
            "source_payload": {"peak_kw": text(row.get("peak_kw")), "tariff": text(row.get("tariff"))},
        },
        flags=flags,
        errors=errors,
    )


def parse_travel_row(tenant, row):
    flags = []
    errors = []
    expense_type = text(row.get("expense_type")).lower()
    quantity, unit, category, co2e = travel_activity(row, expense_type, flags)
    return ParsedActivity(
        fields={
            "external_id": text(row.get("trip_id") or row.get("expense_id")),
            "scope": EmissionActivity.SCOPE_3,
            "category": category,
            "activity_date": parse_date(row.get("start_date"), errors),
            "supplier": text(row.get("vendor")),
            "description": f"{text(row.get('traveler'))}: {text(row.get('origin'))} to {text(row.get('destination'))}",
            "original_quantity": decimal_or_none(row.get("distance")),
            "original_unit": text(row.get("distance_unit")),
            "quantity": quantity,
            "unit": unit,
            "amount": decimal_or_none(row.get("amount")),
            "currency": text(row.get("currency")),
            "co2e_kg": co2e,
            "source_payload": {"traveler": text(row.get("traveler")), "expense_type": expense_type},
        },
        flags=flags,
        errors=errors,
    )


def travel_activity(row, expense_type, flags):
    if expense_type == "flight":
        distance = decimal_or_none(row.get("distance"))
        unit = text(row.get("distance_unit")) or "km"
        if distance is None:
            origin = text(row.get("origin")).upper()
            destination = text(row.get("destination")).upper()
            distance = AIRPORT_DISTANCE_KM.get((origin, destination)) or AIRPORT_DISTANCE_KM.get((destination, origin))
            flags.append("Flight distance estimated from airport pair")
        normalized_unit, km = normalize_unit(distance, unit, [])
        return km, normalized_unit, "business travel - flight", km * EMISSION_FACTORS["flight_km"] if km else None
    if expense_type == "hotel":
        nights = decimal_or_none(row.get("nights")) or Decimal("1")
        return nights, "night", "business travel - hotel", nights * EMISSION_FACTORS["hotel_night"]
    if expense_type == "rail":
        km = normalize_unit(decimal_or_none(row.get("distance")), text(row.get("distance_unit")) or "km", [])[1]
        return km, "km", "business travel - rail", km * EMISSION_FACTORS["rail_km"] if km else None
    if expense_type in {"taxi", "rideshare"}:
        km = normalize_unit(decimal_or_none(row.get("distance")), text(row.get("distance_unit")) or "km", [])[1]
        return km, "km", "business travel - ground transport", km * EMISSION_FACTORS["taxi_km"] if km else None
    km = normalize_unit(decimal_or_none(row.get("distance")), text(row.get("distance_unit")) or "km", [])[1]
    return km, "km", "business travel - rental car", km * EMISSION_FACTORS["rental_car_km"] if km else None


def normalize_unit(value, unit, errors):
    if value is None:
        errors.append("Missing quantity")
        return text(unit), None
    key = text(unit).lower()
    if key not in UNIT_ALIASES:
        errors.append(f"Unsupported unit: {unit}")
        return text(unit), value
    normalized_unit, factor = UNIT_ALIASES[key]
    return normalized_unit, value * factor


def estimate_sap_emissions(material_text, unit, quantity, amount):
    if quantity is None:
        return None
    material = material_text.lower()
    if "diesel" in material and unit == "L":
        return quantity * EMISSION_FACTORS["diesel_l"]
    if "natural gas" in material and unit == "MMBtu":
        return quantity * EMISSION_FACTORS["natural_gas_mmbtu"]
    if amount is not None:
        return amount * EMISSION_FACTORS["procurement_usd"]
    return None


def looks_like_fuel(value):
    lowered = value.lower()
    return "diesel" in lowered or "natural gas" in lowered or "fuel" in lowered


def parse_date(value, errors):
    raw = text(value)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        errors.append(f"Unsupported date: {raw}")
        return None


def decimal_or_none(value):
    raw = text(value).replace(",", "")
    if raw == "":
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def text(value):
    return str(value or "").strip()
