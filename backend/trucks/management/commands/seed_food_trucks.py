"""
Loads sample food trucks so the map has something to show during development.

Usage (from the project root):
    docker compose exec backend python manage.py seed_food_trucks
    docker compose exec backend python manage.py seed_food_trucks --replace

Sample trucks only touch rows whose names start with "[Sample]",
so trucks entered by hand in the admin are never changed or deleted.
Running it again only adds sample trucks that don't exist yet.

Covers Redlands CA plus Denver, Kansas City, New York, Chicago, Miami, and
Seattle, so place search (e.g. "Denver, CO") has trucks to show outside Redlands.
"""

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from trucks.models import FoodTruck

SAMPLE_NAME_PREFIX = "[Sample] "

# (name, cuisine, latitude, longitude, is_open), grouped by area.
# A spread of distances from each downtown lets the radius slider
# visibly add and remove trucks. Names are made up.
SAMPLE_FOOD_TRUCKS = [
    # --- Redlands / Inland Empire, CA (downtown Redlands = 34.0556, -117.1825) ---
    ("Downtown Tacos", "Mexican", 34.0556, -117.1825, True),           # downtown Redlands
    ("University Street Pho", "Vietnamese", 34.0630, -117.1650, True),  # ~1 mi
    ("Smiley Park Smash Burgers", "Burgers", 34.0480, -117.1890, False),
    ("Citrus Plaza Kettle Corn", "Snacks", 34.0700, -117.2150, True),   # ~2 mi
    ("Loma Linda BBQ", "Barbecue", 34.0483, -117.2611, True),           # ~4.5 mi
    ("Yucaipa Wood-Fired Pizza", "Pizza", 34.0336, -117.0431, True),    # ~8 mi
    ("SB Birria Bros", "Mexican", 34.1083, -117.2898, True),            # ~7 mi
    ("Riverside Ramen Cart", "Japanese", 33.9806, -117.3755, False),    # ~12 mi

    # --- Denver, CO (downtown / Civic Center = 39.7392, -104.9903) ---
    ("Civic Center Green Chile", "New Mexican", 39.7365, -104.9875, True),        # ~0.2 mi
    ("Capitol Hill Crepes", "French", 39.7317, -104.98, True),                    # ~0.8 mi
    ("Larimer Lane Dumplings", "Chinese", 39.7477, -104.9995, False),             # ~0.8 mi
    ("Union Station Bagel Wagon", "Breakfast", 39.7527, -105.0002, True),         # ~1.1 mi
    ("Highlands Hot Chicken", "Southern", 39.762, -105.011, False),               # ~1.9 mi
    ("RiNo Rolling Ramen", "Japanese", 39.769, -104.981, True),                   # ~2.1 mi
    ("Cherry Creek Poke Bowl", "Hawaiian", 39.717, -104.953, True),               # ~2.5 mi
    ("Wash Park Wood-Fired Pizza", "Pizza", 39.699, -104.97, True),               # ~3.0 mi
    ("Sloan's Lake Smokehouse", "Barbecue", 39.748, -105.047, True),              # ~3.1 mi

    # --- Kansas City, MO (downtown = 39.0997, -94.5786) ---
    ("Power & Light Burnt Ends", "Barbecue", 39.0985, -94.583, True),             # ~0.3 mi
    ("Crossroads Taco Truck", "Mexican", 39.091, -94.581, False),                 # ~0.6 mi
    ("River Market Empanadas", "Argentine", 39.1098, -94.5822, True),             # ~0.7 mi
    ("Union Station Pretzel Cart", "Snacks", 39.0846, -94.5859, True),            # ~1.1 mi
    ("18th & Vine Fried Catfish", "Southern", 39.091, -94.561, True),             # ~1.1 mi
    ("Northland Noodle Bus", "Thai", 39.142, -94.573, True),                      # ~2.9 mi
    ("Westport Wing Wagon", "Wings", 39.053, -94.592, True),                      # ~3.3 mi
    ("Plaza Gelato Truck", "Desserts", 39.042, -94.593, False),                   # ~4.1 mi
    ("Waldo Brisket Box", "Barbecue", 38.996, -94.592, True),                     # ~7.2 mi

    # --- New York, NY (City Hall, Lower Manhattan = 40.7128, -74.006) ---
    ("Wall Street Halal Cart", "Middle Eastern", 40.706, -74.009, True),          # ~0.5 mi
    ("Battery Park Lobster Rolls", "Seafood", 40.7033, -74.017, True),            # ~0.9 mi
    ("DUMBO Dumpling Truck", "Chinese", 40.7033, -73.9881, True),                 # ~1.1 mi
    ("Washington Square Waffles", "Desserts", 40.7308, -73.9973, True),           # ~1.3 mi
    ("Union Square Dosa Wagon", "Indian", 40.7359, -73.9911, False),              # ~1.8 mi
    ("Williamsburg Arepa Bus", "Venezuelan", 40.7081, -73.9571, True),            # ~2.6 mi
    ("Bryant Park Pretzel Stand", "Snacks", 40.7536, -73.9832, True),             # ~3.1 mi
    ("Long Island City Tacos", "Mexican", 40.7447, -73.9485, False),              # ~3.7 mi
    ("Columbus Circle Coffee Cart", "Coffee", 40.7681, -73.9819, True),           # ~4.0 mi

    # --- Chicago, IL (the Loop = 41.8781, -87.6298) ---
    ("Daley Plaza Italian Beef", "Sandwiches", 41.884, -87.6301, True),           # ~0.4 mi
    ("Millennium Park Popcorn", "Snacks", 41.8826, -87.6226, True),               # ~0.5 mi
    ("Fulton Market Falafel", "Middle Eastern", 41.8866, -87.648, False),         # ~1.1 mi
    ("Navy Pier Polish Sausage", "Hot Dogs", 41.8917, -87.6086, True),            # ~1.4 mi
    ("Chinatown Bao Truck", "Chinese", 41.8526, -87.6322, True),                  # ~1.8 mi
    ("Lincoln Park Deep Dish", "Pizza", 41.9214, -87.6513, False),                # ~3.2 mi
    ("Wicker Park Pierogi", "Polish", 41.9088, -87.6796, True),                   # ~3.3 mi
    ("Wrigleyville Hot Dog Wagon", "Hot Dogs", 41.9484, -87.6553, True),          # ~5.0 mi
    ("Hyde Park Jerk Chicken", "Caribbean", 41.7943, -87.5907, True),             # ~6.1 mi

    # --- Miami, FL (downtown = 25.7741, -80.1936) ---
    ("Bayfront Park Ceviche", "Peruvian", 25.7753, -80.1861, True),               # ~0.5 mi
    ("Brickell Cuban Sandwich Co", "Cuban", 25.7617, -80.1918, True),             # ~0.9 mi
    ("Calle Ocho Cafecito Cart", "Coffee", 25.7656, -80.219, True),               # ~1.7 mi
    ("Wynwood Smoothie Bus", "Drinks", 25.801, -80.199, True),                    # ~1.9 mi
    ("Design District Tostones", "Latin", 25.813, -80.193, False),                # ~2.7 mi
    ("South Beach Fish Tacos", "Seafood", 25.781, -80.13, True),                  # ~4.0 mi
    ("Coconut Grove Empanadas", "Argentine", 25.728, -80.237, False),             # ~4.2 mi
    ("Coral Gables Arepas", "Colombian", 25.749, -80.261, True),                  # ~4.5 mi

    # --- Seattle, WA (downtown = 47.6062, -122.3321) ---
    ("Pioneer Square Teriyaki", "Japanese", 47.6015, -122.3343, True),            # ~0.3 mi
    ("Pike Place Chowder Cart", "Seafood", 47.6097, -122.3422, True),             # ~0.5 mi
    ("Seattle Center Mini Donuts", "Desserts", 47.6205, -122.3493, True),         # ~1.3 mi
    ("South Lake Union Pho", "Vietnamese", 47.6256, -122.3344, False),            # ~1.3 mi
    ("Capitol Hill Banh Mi", "Vietnamese", 47.6253, -122.3222, True),             # ~1.4 mi
    ("Fremont Fish & Chips", "Seafood", 47.651, -122.35, True),                   # ~3.2 mi
    ("U-District Hom Bao", "Chinese", 47.6588, -122.313, False),                  # ~3.7 mi
    ("Alki Beach Salmon Shack", "Seafood", 47.579, -122.41, True),                # ~4.1 mi
    ("Ballard Smoked Salmon Wagon", "Scandinavian", 47.6687, -122.3847, True),    # ~5.0 mi
]


class Command(BaseCommand):
    help = "Create sample food trucks in Redlands and six other US cities for local development."

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
