from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import FoodTruck

# Reference point: downtown Redlands, CA (longitude, latitude)
REDLANDS_LONGITUDE = -117.1825
REDLANDS_LATITUDE = 34.0556


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
