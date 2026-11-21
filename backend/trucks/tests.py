import json
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .management.commands.seed_food_trucks import SAMPLE_FOOD_TRUCKS, SAMPLE_TRUCK_NAMES
from .models import FoodTruck, Review
from .place_search import RATE_GATE_CACHE_KEY

# Reference point: downtown Redlands, CA (longitude, latitude)
REDLANDS_LONGITUDE = -117.1825
REDLANDS_LATITUDE = 34.0556


# A new truck as GeoJSON, the shape FoodTruckSerializer accepts
NEW_TRUCK_FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-117.1825, 34.0556]},
    "properties": {"name": "Brand New Truck", "cuisine": "Tacos"},
}


class NearbyFoodTruckTests(APITestCase):
    def setUp(self):
        # ~0 miles away
        self.downtown_truck = FoodTruck.objects.create(
            name="Downtown Tacos",
            location=Point(REDLANDS_LONGITUDE, REDLANDS_LATITUDE, srid=4326),
            is_open=True,
        )
        # San Bernardino, roughly 8-9 miles away
        self.san_bernardino_truck = FoodTruck.objects.create(
            name="SB Burgers",
            location=Point(-117.2898, 34.1083, srid=4326),
            is_open=False,
        )
        # Los Angeles, roughly 60 miles away
        self.los_angeles_truck = FoodTruck.objects.create(
            name="LA Noodles",
            location=Point(-118.2437, 34.0522, srid=4326),
            is_open=True,
        )

    def get_nearby(self, **extra_parameters):
        query_parameters = {
            "latitude": REDLANDS_LATITUDE,
            "longitude": REDLANDS_LONGITUDE,
            **extra_parameters,
        }
        return self.client.get("/api/trucks/nearby/", query_parameters)

    def truck_names(self, response):
        return [feature["properties"]["name"] for feature in response.data["features"]]

    def test_default_five_mile_radius_only_returns_close_truck(self):
        response = self.get_nearby()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.truck_names(response), ["Downtown Tacos"])

    def test_larger_radius_includes_more_trucks_sorted_by_distance(self):
        response = self.get_nearby(radius_miles=15)
        self.assertEqual(self.truck_names(response), ["Downtown Tacos", "SB Burgers"])
        san_bernardino_distance = response.data["features"][1]["properties"]["distance_miles"]
        self.assertGreater(san_bernardino_distance, 5)
        self.assertLess(san_bernardino_distance, 15)

    def test_open_only_filter(self):
        response = self.get_nearby(radius_miles=15, open_only="true")
        self.assertEqual(self.truck_names(response), ["Downtown Tacos"])

    def test_missing_latitude_is_rejected(self):
        response = self.client.get("/api/trucks/nearby/", {"longitude": REDLANDS_LONGITUDE})
        self.assertEqual(response.status_code, 400)

    def test_radius_above_maximum_is_rejected(self):
        response = self.get_nearby(radius_miles=500)
        self.assertEqual(response.status_code, 400)

    def test_anonymous_user_cannot_create_truck(self):
        response = self.client.post("/api/trucks/", {"name": "Sneaky Truck"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_regular_user_cannot_create_truck(self):
        # Anyone can sign up, so a plain customer account must not be able to add trucks
        customer = get_user_model().objects.create_user(username="hungry_customer", password="test-password-123")
        self.client.force_login(customer)
        response = self.client.post("/api/trucks/", NEW_TRUCK_FEATURE, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(FoodTruck.objects.filter(name="Brand New Truck").exists())

    def test_staff_can_create_truck(self):
        staff_user = get_user_model().objects.create_user(
            username="admin_person", password="test-password-123", is_staff=True
        )
        self.client.force_login(staff_user)
        response = self.client.post("/api/trucks/", NEW_TRUCK_FEATURE, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(FoodTruck.objects.get(name="Brand New Truck").owner, staff_user)


class OwnerCheckInTests(APITestCase):
    """Owner check-in / check-out, permissions, and automatic closing."""

    def setUp(self):
        user_model = get_user_model()
        self.truck_owner = user_model.objects.create_user(username="taco_owner", password="test-password-123")
        self.other_user = user_model.objects.create_user(username="someone_else", password="test-password-123")
        self.staff_user = user_model.objects.create_user(
            username="admin_person", password="test-password-123", is_staff=True
        )
        # Starts closed, parked in Los Angeles (~60 miles from Redlands)
        self.food_truck = FoodTruck.objects.create(
            name="Taco Owner Truck",
            location=Point(-118.2437, 34.0522, srid=4326),
            is_open=False,
            owner=self.truck_owner,
        )
        self.check_in_url = f"/api/trucks/{self.food_truck.id}/check-in/"
        self.check_out_url = f"/api/trucks/{self.food_truck.id}/check-out/"

    def check_in_payload(self, hours_from_now=3):
        """Check in at downtown Redlands, open for the given number of hours."""
        return {
            "latitude": REDLANDS_LATITUDE,
            "longitude": REDLANDS_LONGITUDE,
            "open_until": (timezone.now() + timedelta(hours=hours_from_now)).isoformat(),
        }

    def nearby_open_truck_names(self):
        response = self.client.get(
            "/api/trucks/nearby/",
            {"latitude": REDLANDS_LATITUDE, "longitude": REDLANDS_LONGITUDE, "radius_miles": 5, "open_only": "true"},
        )
        return [feature["properties"]["name"] for feature in response.data["features"]]

    def test_owner_check_in_moves_truck_and_customers_see_it(self):
        self.assertEqual(self.nearby_open_truck_names(), [])  # not nearby, not open yet

        self.client.force_login(self.truck_owner)
        response = self.client.post(self.check_in_url, self.check_in_payload(), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["properties"]["is_open"])

        self.client.logout()  # customers are anonymous
        self.assertEqual(self.nearby_open_truck_names(), ["Taco Owner Truck"])

    def test_other_user_cannot_check_in_someone_elses_truck(self):
        self.client.force_login(self.other_user)
        response = self.client.post(self.check_in_url, self.check_in_payload(), format="json")
        self.assertEqual(response.status_code, 403)
        self.food_truck.refresh_from_db()
        self.assertFalse(self.food_truck.is_open)

    def test_anonymous_user_cannot_check_in(self):
        response = self.client.post(self.check_in_url, self.check_in_payload(), format="json")
        self.assertEqual(response.status_code, 403)

    def test_staff_can_check_in_any_truck(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(self.check_in_url, self.check_in_payload(), format="json")
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_edit_or_delete_truck(self):
        self.client.force_login(self.other_user)
        truck_detail_url = f"/api/trucks/{self.food_truck.id}/"
        self.assertEqual(self.client.patch(truck_detail_url, {"name": "Hijacked"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(truck_detail_url).status_code, 403)

    def test_check_out_closes_truck(self):
        self.client.force_login(self.truck_owner)
        self.client.post(self.check_in_url, self.check_in_payload(), format="json")
        response = self.client.post(self.check_out_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["properties"]["is_open"])
        self.assertEqual(self.nearby_open_truck_names(), [])

    def test_truck_closes_automatically_after_open_until(self):
        # Simulate an owner who checked in earlier and never checked out
        self.food_truck.location = Point(REDLANDS_LONGITUDE, REDLANDS_LATITUDE, srid=4326)
        self.food_truck.is_open = True
        self.food_truck.open_until = timezone.now() - timedelta(minutes=1)
        self.food_truck.save()

        self.assertEqual(self.nearby_open_truck_names(), [])  # filtered out of "open now"
        response = self.client.get(f"/api/trucks/{self.food_truck.id}/")
        self.assertFalse(response.data["properties"]["is_open"])  # and reported as closed

    def test_closing_time_in_the_past_is_rejected(self):
        self.client.force_login(self.truck_owner)
        response = self.client.post(self.check_in_url, self.check_in_payload(hours_from_now=-1), format="json")
        self.assertEqual(response.status_code, 400)

    def test_closing_time_too_far_ahead_is_rejected(self):
        self.client.force_login(self.truck_owner)
        response = self.client.post(self.check_in_url, self.check_in_payload(hours_from_now=30), format="json")
        self.assertEqual(response.status_code, 400)

    def test_customer_can_review_someone_elses_truck(self):
        # Regression: the owner-or-staff check used to block every customer review
        self.client.force_login(self.other_user)
        response = self.client.post(
            f"/api/trucks/{self.food_truck.id}/reviews/", {"rating": 4, "comment": "Tasty"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_owner_cannot_review_own_truck(self):
        self.client.force_login(self.truck_owner)
        response = self.client.post(f"/api/trucks/{self.food_truck.id}/reviews/", {"rating": 5}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_anonymous_user_cannot_review(self):
        response = self.client.post(f"/api/trucks/{self.food_truck.id}/reviews/", {"rating": 5}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_mine_lists_only_owned_trucks(self):
        FoodTruck.objects.create(name="Not Theirs", location=Point(-117.18, 34.05, srid=4326), owner=self.other_user)
        self.client.force_login(self.truck_owner)
        response = self.client.get("/api/trucks/mine/")
        self.assertEqual([feature["properties"]["name"] for feature in response.data["features"]], ["Taco Owner Truck"])


class LoginTests(APITestCase):
    """Session login as the browser does it, with real CSRF checking turned on."""

    def setUp(self):
        get_user_model().objects.create_user(username="taco_owner", password="test-password-123")
        self.browser_client = APIClient(enforce_csrf_checks=True)

    def get_csrf_token(self):
        self.browser_client.get("/api/auth/csrf/")
        return self.browser_client.cookies["csrftoken"].value

    def test_login_with_csrf_token_succeeds_and_me_works(self):
        csrf_token = self.get_csrf_token()
        response = self.browser_client.post(
            "/api/auth/login/",
            {"username": "taco_owner", "password": "test-password-123"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.browser_client.get("/api/auth/me/").data["username"], "taco_owner")

    def test_login_without_csrf_token_is_rejected(self):
        self.get_csrf_token()
        response = self.browser_client.post(
            "/api/auth/login/", {"username": "taco_owner", "password": "test-password-123"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_wrong_password_is_rejected(self):
        csrf_token = self.get_csrf_token()
        response = self.browser_client.post(
            "/api/auth/login/",
            {"username": "taco_owner", "password": "wrong"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 400)

    def test_me_is_forbidden_when_logged_out(self):
        self.assertEqual(self.browser_client.get("/api/auth/me/").status_code, 403)


class RegistrationTests(APITestCase):
    """Customer sign-up as the browser does it, with real CSRF checking turned on."""

    def setUp(self):
        # Throttle counts live in the cache; start every test with a clean slate
        cache.clear()
        get_user_model().objects.create_user(
            username="taco_owner", email="owner@example.com", password="test-password-123"
        )
        self.browser_client = APIClient(enforce_csrf_checks=True)

    def get_csrf_token(self):
        self.browser_client.get("/api/auth/csrf/")
        return self.browser_client.cookies["csrftoken"].value

    def register(self, with_csrf_token=True, **field_overrides):
        """POST a valid sign-up form, with any fields replaced by field_overrides."""
        form_fields = {
            "username": "hungry_customer",
            "email": "customer@example.com",
            "password": "grilled-cheese-42",
            "password_confirmation": "grilled-cheese-42",
        }
        form_fields.update(field_overrides)
        csrf_header = {"HTTP_X_CSRFTOKEN": self.get_csrf_token()} if with_csrf_token else {}
        return self.browser_client.post("/api/auth/register/", form_fields, format="json", **csrf_header)

    def test_register_creates_customer_account(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, {"username": "hungry_customer", "is_staff": False})
        new_user = get_user_model().objects.get(username="hungry_customer")
        self.assertEqual(new_user.email, "customer@example.com")
        self.assertFalse(new_user.is_staff)
        self.assertTrue(new_user.check_password("grilled-cheese-42"))  # stored hashed, not plain text

    def test_user_is_logged_in_after_register(self):
        self.register()
        response = self.browser_client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "hungry_customer")

    def test_new_customer_can_leave_review(self):
        # End to end: sign up, then post a review using the same session
        food_truck = FoodTruck.objects.create(name="Review Me", location=Point(-117.18, 34.05, srid=4326))
        self.register()
        response = self.browser_client.post(
            f"/api/trucks/{food_truck.id}/reviews/",
            {"rating": 5, "comment": "Great tacos"},
            format="json",
            HTTP_X_CSRFTOKEN=self.browser_client.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 201)

    def test_duplicate_username_is_rejected(self):
        response = self.register(username="taco_owner")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_duplicate_username_with_different_capitals_is_rejected(self):
        response = self.register(username="Taco_Owner")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_duplicate_email_is_rejected(self):
        response = self.register(email="OWNER@example.com")  # case doesn't matter
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_missing_email_is_rejected(self):
        response = self.register(email="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_weak_password_is_rejected(self):
        # Fails Django's common-password, numeric and minimum-length validators
        response = self.register(password="12345", password_confirmation="12345")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)
        self.assertFalse(get_user_model().objects.filter(username="hungry_customer").exists())

    def test_password_too_similar_to_username_is_rejected(self):
        response = self.register(password="hungry_customer1", password_confirmation="hungry_customer1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_mismatched_passwords_are_rejected(self):
        response = self.register(password_confirmation="something-else-42")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirmation", response.data)

    def test_register_without_csrf_token_is_rejected(self):
        self.get_csrf_token()  # the cookie exists, but the header is missing
        response = self.register(with_csrf_token=False)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user_model().objects.filter(username="hungry_customer").exists())

    def test_register_cannot_create_staff_account(self):
        response = self.register(is_staff=True, is_superuser=True)  # extra fields are ignored
        self.assertEqual(response.status_code, 201)
        new_user = get_user_model().objects.get(username="hungry_customer")
        self.assertFalse(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)

    def test_too_many_attempts_are_throttled(self):
        # Read the limit from settings so this test follows any change to the rate
        allowed_attempts = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["register"].split("/")[0])
        for attempt_number in range(allowed_attempts):
            response = self.register(username=f"customer_{attempt_number}", email=f"customer{attempt_number}@example.com")
            self.assertEqual(response.status_code, 201)
            self.browser_client.post(
                "/api/auth/logout/", HTTP_X_CSRFTOKEN=self.browser_client.cookies["csrftoken"].value
            )
        response = self.register(username="one_too_many", email="one_too_many@example.com")
        self.assertEqual(response.status_code, 429)
        self.assertFalse(get_user_model().objects.filter(username="one_too_many").exists())


# What Nominatim's jsonv2 format sends back (lat/lon arrive as strings)
SAMPLE_NOMINATIM_RESPONSE = [
    {"display_name": "Riverside, Riverside County, California, United States", "lat": "33.9533", "lon": "-117.3962"},
    {"display_name": "Riverside, Cook County, Illinois, United States", "lat": "41.8350", "lon": "-87.8228"},
]


def fake_nominatim_response(response_body):
    """Stands in for urlopen's return value, which is used as a context manager."""
    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps(response_body).encode("utf-8")
    fake_response.__enter__.return_value = fake_response
    return fake_response


# Patch where place_search looks up urlopen, so no test ever calls the real server
@patch("trucks.place_search.urlopen")
class PlaceSearchTests(APITestCase):
    def setUp(self):
        # Each test starts with no cached results and an open rate gate
        cache.clear()

    def search(self, search_text):
        return self.client.get("/api/places/search/", {"query": search_text})

    def test_returns_places_with_numeric_coordinates(self, mock_urlopen):
        mock_urlopen.return_value = fake_nominatim_response(SAMPLE_NOMINATIM_RESPONSE)
        response = self.search("Riverside")
        self.assertEqual(response.status_code, 200)
        first_place = response.data["results"][0]
        self.assertEqual(first_place["display_name"], SAMPLE_NOMINATIM_RESPONSE[0]["display_name"])
        self.assertEqual(first_place["latitude"], 33.9533)
        self.assertEqual(first_place["longitude"], -117.3962)

    def test_sends_identifying_user_agent_and_country_filter(self, mock_urlopen):
        mock_urlopen.return_value = fake_nominatim_response(SAMPLE_NOMINATIM_RESPONSE)
        self.search("Riverside")
        sent_request = mock_urlopen.call_args.args[0]
        self.assertIn("LocalBites", sent_request.get_header("User-agent"))
        self.assertIn("format=jsonv2", sent_request.full_url)
        self.assertIn("countrycodes=us", sent_request.full_url)

    def test_repeat_search_is_served_from_cache(self, mock_urlopen):
        mock_urlopen.return_value = fake_nominatim_response(SAMPLE_NOMINATIM_RESPONSE)
        self.search("Riverside, CA")
        # Different spacing and capitalization still hits the same cache entry
        response = self.search("  riverside,   ca ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_urlopen.call_count, 1)

    def test_too_short_query_is_rejected_without_calling_nominatim(self, mock_urlopen):
        response = self.search("a")
        self.assertEqual(response.status_code, 400)
        mock_urlopen.assert_not_called()

    def test_missing_query_is_rejected(self, mock_urlopen):
        response = self.client.get("/api/places/search/")
        self.assertEqual(response.status_code, 400)

    def test_busy_rate_gate_returns_429(self, mock_urlopen):
        # Simulate another request having used this second's Nominatim slot
        cache.add(RATE_GATE_CACHE_KEY, True, timeout=60)
        response = self.search("Fontana")
        self.assertEqual(response.status_code, 429)
        mock_urlopen.assert_not_called()

    def test_network_failure_returns_502(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("connection refused")
        response = self.search("Fontana")
        self.assertEqual(response.status_code, 502)

    def test_unexpected_response_shape_returns_502(self, mock_urlopen):
        mock_urlopen.return_value = fake_nominatim_response([{"name": "no coordinates here"}])
        response = self.search("Fontana")
        self.assertEqual(response.status_code, 502)

    def test_failed_search_is_not_cached(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("connection refused")
        self.search("Fontana")
        # Reopen the gate, fix the "network", and search again: Nominatim must be called
        cache.delete(RATE_GATE_CACHE_KEY)
        mock_urlopen.side_effect = None
        mock_urlopen.return_value = fake_nominatim_response(SAMPLE_NOMINATIM_RESPONSE)
        response = self.search("Fontana")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_urlopen.call_count, 2)


# Downtown point for each seeded city (latitude, longitude) and how many
# sample trucks the seed command puts within 10 miles of it
SEEDED_CITY_CENTERS = {
    "Denver, CO": (39.7392, -104.9903, 9),
    "Kansas City, MO": (39.0997, -94.5786, 9),
    "New York, NY": (40.7128, -74.0060, 9),
    "Chicago, IL": (41.8781, -87.6298, 9),
    "Miami, FL": (25.7741, -80.1936, 8),
    "Seattle, WA": (47.6062, -122.3321, 9),
}


class SeedFoodTrucksCommandTests(APITestCase):
    def run_seed_command(self, *arguments):
        # Swallow the command's progress messages so test output stays clean
        call_command("seed_food_trucks", *arguments, stdout=StringIO())

    def test_creates_every_sample_truck(self):
        self.run_seed_command()
        self.assertEqual(FoodTruck.objects.filter(name__in=SAMPLE_TRUCK_NAMES).count(), len(SAMPLE_FOOD_TRUCKS))
        # Names are plain now, with no "[Sample]" tag
        self.assertFalse(FoodTruck.objects.filter(name__startswith="[Sample]").exists())

    def test_each_city_shows_only_its_own_trucks_in_a_nearby_search(self):
        self.run_seed_command()
        for city_name, (latitude, longitude, expected_truck_count) in SEEDED_CITY_CENTERS.items():
            with self.subTest(city=city_name):
                response = self.client.get(
                    "/api/trucks/nearby/",
                    {"latitude": latitude, "longitude": longitude, "radius_miles": 10},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.data["features"]), expected_truck_count)

    def test_running_twice_does_not_duplicate_trucks(self):
        self.run_seed_command()
        self.run_seed_command()
        self.assertEqual(FoodTruck.objects.count(), len(SAMPLE_FOOD_TRUCKS))

    def test_replace_keeps_hand_entered_trucks(self):
        hand_entered_truck = FoodTruck.objects.create(
            name="Real Owner Truck", location=Point(-104.99, 39.74, srid=4326)
        )
        self.run_seed_command()
        self.run_seed_command("--replace")
        self.assertTrue(FoodTruck.objects.filter(pk=hand_entered_truck.pk).exists())
        self.assertEqual(FoodTruck.objects.count(), len(SAMPLE_FOOD_TRUCKS) + 1)


class RemoveSamplePrefixMigrationTests(APITestCase):
    """Runs the 0005 data migration's rename function against test rows."""

    def run_rename(self):
        # Migration modules start with a digit, so import them by string
        from importlib import import_module

        from django.apps import apps as installed_apps

        migration_module = import_module("trucks.migrations.0005_remove_sample_name_prefix")
        migration_module.remove_sample_prefix(installed_apps, schema_editor=None)

    def create_truck(self, truck_name):
        return FoodTruck.objects.create(name=truck_name, location=Point(-104.99, 39.74, srid=4326))

    def test_renames_tagged_truck_in_place_and_keeps_its_reviews(self):
        tagged_truck = self.create_truck("[Sample] Downtown Tacos")
        reviewer = get_user_model().objects.create_user(username="reviewer", password="test-password-123")
        Review.objects.create(truck=tagged_truck, user=reviewer, rating=5)
        self.run_rename()
        tagged_truck.refresh_from_db()
        self.assertEqual(tagged_truck.name, "Downtown Tacos")
        # Same row, so the review is still attached
        self.assertEqual(tagged_truck.reviews.count(), 1)

    def test_leaves_tagged_truck_alone_when_plain_name_already_exists(self):
        self.create_truck("Downtown Tacos")
        tagged_truck = self.create_truck("[Sample] Downtown Tacos")
        self.run_rename()
        tagged_truck.refresh_from_db()
        self.assertEqual(tagged_truck.name, "[Sample] Downtown Tacos")
        self.assertEqual(FoodTruck.objects.count(), 2)

    def test_does_not_touch_hand_entered_trucks(self):
        hand_entered_truck = self.create_truck("Real Owner Truck")
        self.run_rename()
        hand_entered_truck.refresh_from_db()
        self.assertEqual(hand_entered_truck.name, "Real Owner Truck")
