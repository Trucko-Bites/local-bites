"""
Loads sample food trucks so the map has something to show during development.

Usage (from the project root):
    docker compose exec backend python manage.py seed_food_trucks
    docker compose exec backend python manage.py seed_food_trucks --replace

Sample trucks only touch rows whose names start with "[Sample]",
so trucks entered by hand in the admin are never changed or deleted.
"""

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from trucks.models import FoodTruck

SAMPLE_NAME_PREFIX = "[Sample] "

# (name, cuisine, latitude, longitude, is_open) around Redlands / the Inland Empire.
# A spread of distances lets the radius slider visibly add and remove trucks.
SAMPLE_FOOD_TRUCKS = [
    ("Downtown Tacos", "Mexican", 34.0556, -117.1825, True),           # downtown Redlands
    ("University Street Pho", "Vietnamese", 34.0630, -117.1650, True),  # ~1 mi
    ("Smiley Park Smash Burgers", "Burgers", 34.0480, -117.1890, False),
    ("Citrus Plaza Kettle Corn", "Snacks", 34.0700, -117.2150, True),   # ~2 mi
    ("Loma Linda BBQ", "Barbecue", 34.0483, -117.2611, True),           # ~4.5 mi
    ("Yucaipa Wood-Fired Pizza", "Pizza", 34.0336, -117.0431, True),    # ~8 mi
    ("SB Birria Bros", "Mexican", 34.1083, -117.2898, True),            # ~7 mi
    ("Riverside Ramen Cart", "Japanese", 33.9806, -117.3755, False),    # ~12 mi
]


class Command(BaseCommand):
    help = "Create sample food trucks around Redlands, CA for local development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing sample trucks first (hand-entered trucks are kept).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["replace"]:
            deleted_count, _ = FoodTruck.objects.filter(name__startswith=SAMPLE_NAME_PREFIX).delete()
            self.stdout.write(f"Removed {deleted_count} existing sample trucks.")

        created_count = 0
        for truck_name, cuisine, latitude, longitude, is_open in SAMPLE_FOOD_TRUCKS:
            # get_or_create makes the command safe to run more than once
            _, was_created = FoodTruck.objects.get_or_create(
                name=f"{SAMPLE_NAME_PREFIX}{truck_name}",
                defaults={
                    "cuisine": cuisine,
                    # GEOS points are (longitude, latitude)
                    "location": Point(longitude, latitude, srid=4326),
                    "is_open": is_open,
                },
            )
            created_count += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            f"Created {created_count} sample trucks "
            f"({len(SAMPLE_FOOD_TRUCKS) - created_count} already existed)."
        ))
