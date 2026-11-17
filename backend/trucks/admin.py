from django.contrib.gis import admin

from .models import FoodTruck


# GISModelAdmin shows an OpenStreetMap-based map widget for picking the location
@admin.register(FoodTruck)
class FoodTruckAdmin(admin.GISModelAdmin):
    list_display = ["name", "cuisine", "owner", "is_open", "open_until", "location_updated_at"]
    list_filter = ["is_open", "cuisine", "owner"]
    search_fields = ["name", "cuisine"]
