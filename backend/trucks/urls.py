from rest_framework.routers import DefaultRouter

from .views import FoodTruckViewSet

# The router builds /trucks/, /trucks/<id>/, and /trucks/nearby/
router = DefaultRouter()
router.register("trucks", FoodTruckViewSet, basename="food-truck")

urlpatterns = router.urls
