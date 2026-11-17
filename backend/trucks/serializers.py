from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import FoodTruck

METERS_PER_MILE = 1609.344
MAXIMUM_CHECK_IN_HOURS = 18


class FoodTruckSerializer(GeoFeatureModelSerializer):
    """
    Outputs each truck as a GeoJSON Feature:
    {"type": "Feature", "geometry": {...point...}, "properties": {...fields...}}
    Leaflet can draw that format directly.
    """

    # Only filled in by the "nearby" endpoint, which annotates distance_from_user
    distance_miles = serializers.SerializerMethodField()
    # Computed: a truck past its open_until time reports as closed
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = FoodTruck
        geo_field = "location"
        fields = [
            "id",
            "name",
            "cuisine",
            "description",
            "is_open",
            "open_until",
            "location_updated_at",
            "distance_miles",
        ]
        # Opening, closing and moving happen through check-in / check-out only
        read_only_fields = ["open_until", "location_updated_at"]

    def get_distance_miles(self, food_truck):
        distance_from_user = getattr(food_truck, "distance_from_user", None)
        if distance_from_user is None:
            return None
        # distance_from_user is a Django Distance object measured in meters
        return round(distance_from_user.m / METERS_PER_MILE, 2)

    def get_is_open(self, food_truck):
        return food_truck.is_currently_open


class CheckInSerializer(serializers.Serializer):
    """Input for POST /api/trucks/<id>/check-in/"""

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    open_until = serializers.DateTimeField()

    def validate_open_until(self, open_until):
        current_time = timezone.now()
        if open_until <= current_time:
            raise serializers.ValidationError("Closing time must be in the future.")
        if open_until > current_time + timedelta(hours=MAXIMUM_CHECK_IN_HOURS):
            raise serializers.ValidationError(
                f"Closing time must be within {MAXIMUM_CHECK_IN_HOURS} hours."
            )
        return open_until
