from django.contrib.gis import admin

from .models import FoodTruck, Review


# GISModelAdmin shows an OpenStreetMap-based map widget for picking the location
@admin.register(FoodTruck)
class FoodTruckAdmin(admin.GISModelAdmin):
    list_display = ["name", "cuisine", "owner",
                    "is_open", "open_until", "location_updated_at"]
    list_filter = ["is_open", "cuisine", "owner"]
    search_fields = ["name", "cuisine"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["truck", "user", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["truck__name", "user__username", "comment"]
