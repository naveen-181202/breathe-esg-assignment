from decimal import Decimal

from django.core.files.base import ContentFile
from django.test import TestCase

from .ingestion import ingest_file
from .models import EmissionActivity, Facility, SourceConnection, Tenant


class IngestionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Co", slug="test-co")
        Facility.objects.create(tenant=self.tenant, code="BLR01", name="Bengaluru", country="India")

    def test_sap_german_headers_are_normalized(self):
        source = SourceConnection.objects.create(
            tenant=self.tenant,
            source_type=SourceConnection.SAP,
            name="SAP",
            ingestion_mode="csv",
        )
        payload = (
            "Werk,Buchungsdatum,Kurztext,Menge,Einheit,Lieferant,Betrag,Wahrung,Beleg\n"
            "BLR01,15.01.2026,DIESEL LOW SULPHUR,10,L,Vendor,100,INR,490\n"
        )
        ingest_file(source, ContentFile(payload.encode("utf-8")), "sap.csv")
        activity = EmissionActivity.objects.get()
        self.assertEqual(activity.scope, EmissionActivity.SCOPE_1)
        self.assertEqual(activity.unit, "L")
        self.assertEqual(activity.co2e_kg, Decimal("26.800"))

    def test_travel_flight_distance_can_be_estimated(self):
        source = SourceConnection.objects.create(
            tenant=self.tenant,
            source_type=SourceConnection.TRAVEL,
            name="Travel",
            ingestion_mode="csv",
        )
        payload = (
            "expense_id,trip_id,traveler,expense_type,start_date,origin,destination,distance,distance_unit,nights,vendor,amount,currency\n"
            "E1,T1,Asha,Flight,2026-01-01,BLR,DEL,,,,IndiGo,100,INR\n"
        )
        ingest_file(source, ContentFile(payload.encode("utf-8")), "travel.csv")
        activity = EmissionActivity.objects.get()
        self.assertIn("Flight distance estimated from airport pair", activity.quality_flags)
        self.assertEqual(activity.quantity, Decimal("1704.000"))
