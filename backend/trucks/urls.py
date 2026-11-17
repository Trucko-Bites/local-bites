from django.urls import path
from rest_framework.routers import DefaultRouter

from .place_views import PlaceSearchView
from .views import FoodTruckViewSet

# The router builds /trucks/, /trucks/<id>/, and /trucks/nearby/
router = DefaultRouter()
router.register("trucks", FoodTruckViewSet, basename="food-truck")

urlpatterns = [
    # Turns a typed city/address into coordinates for "search a different area"
    path("places/search/", PlaceSearchView.as_view(), name="place-search"),
    *router.urls,
]
