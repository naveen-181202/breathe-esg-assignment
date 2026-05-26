from pathlib import Path

from django.core.files.base import File
from django.core.management.base import BaseCommand

from core.ingestion import ingest_file
from core.models import Facility, SourceConnection, Tenant


class Command(BaseCommand):
    help = "Seeds the demo tenant, sources, facilities, and sample ingestions."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(name="Acme Industries", slug="acme-industries")
        facilities = [
            ("BLR01", "Bengaluru Manufacturing", "India"),
            ("PUN02", "Pune Assembly", "India"),
        ]
        for code, name, country in facilities:
            Facility.objects.get_or_create(tenant=tenant, code=code, defaults={"name": name, "country": country})

        sources = [
            (
                SourceConnection.SAP,
                "SAP S/4HANA material and purchase export",
                "CSV upload mirroring flattened OData entity export",
                "sap_fuel_procurement.csv",
            ),
            (
                SourceConnection.UTILITY,
                "Facilities utility portal export",
                "CSV upload from utility billing portal",
                "utility_electricity.csv",
            ),
            (
                SourceConnection.TRAVEL,
                "Concur-like travel expense export",
                "CSV upload from travel platform report",
                "travel_concur_export.csv",
            ),
        ]
        sample_dir = Path(__file__).resolve().parents[4] / "sample_data"
        for source_type, name, mode, filename in sources:
            source, _ = SourceConnection.objects.get_or_create(
                tenant=tenant,
                source_type=source_type,
                name=name,
                defaults={"ingestion_mode": mode, "details": {"sample_file": filename}},
            )
            if source.batches.filter(filename=filename).exists():
                continue
            with (sample_dir / filename).open("rb") as handle:
                ingest_file(source, File(handle), filename, actor="seed_demo")

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
