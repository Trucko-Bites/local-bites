from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from rest_framework import status, viewsets
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_gis.pagination import GeoJsonPagination

from .models import FoodTruck, Review
from .permissions import IsOwnerOrStaffOrReadOnly
from .serializers import CheckInSerializer, FoodTruckSerializer, ReviewSerializer

DEFAULT_RADIUS_MILES = 5
MAXIMUM_RADIUS_MILES = 50
MAXIMUM_NEARBY_RESULTS = 100


def read_float_parameter(query_parameters, parameter_name, minimum_value, maximum_value, default_value=None):
    """Read a number from the query string and reject anything out of range."""
    raw_value = query_parameters.get(parameter_name, default_value)
    if raw_value is None:
        raise ValidationError(
            {parameter_name: "This query parameter is required."})
    try:
        parsed_value = float(raw_value)
    except (TypeError, ValueError):
        raise ValidationError({parameter_name: "Must be a number."})
    if not minimum_value <= parsed_value <= maximum_value:
        raise ValidationError(
            {parameter_name: f"Must be between {minimum_value} and {maximum_value}."})
    return parsed_value


class FoodTruckViewSet(viewsets.ModelViewSet):
    """
    /api/trucks/                  list (paginated GeoJSON) / create
    /api/trucks/<id>/             retrieve / update / delete (owner or staff)
    /api/trucks/nearby/           trucks within a radius of the user, closest first
    /api/trucks/mine/             trucks the logged-in user can check in
    /api/trucks/<id>/check-in/    owner sets location + closing time, opens the truck
    /api/trucks/<id>/check-out/   owner closes the truck now
    """

    queryset = FoodTruck.objects.with_rating_summary()
    serializer_class = FoodTruckSerializer
    pagination_class = GeoJsonPagination
    permission_classes = [IsOwnerOrStaffOrReadOnly]

    def perform_create(self, serializer):
        # Only staff can create (see IsOwnerOrStaffOrReadOnly). The creator starts
        # as the owner; staff hand the truck to its real owner in Django admin.
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def nearby(self, request):
        """
        GET /api/trucks/nearby/?latitude=34.0556&longitude=-117.1825&radius_miles=5
        Optional: open_only=true
        """
        latitude = read_float_parameter(
            request.query_params, "latitude", -90, 90)
        longitude = read_float_parameter(
            request.query_params, "longitude", -180, 180)
        radius_miles = read_float_parameter(
            request.query_params, "radius_miles", 0.1, MAXIMUM_RADIUS_MILES, DEFAULT_RADIUS_MILES
        )

        # GEOS points are (x, y) = (longitude, latitude) -- easy to flip by mistake
        user_point = Point(longitude, latitude, srid=4326)

        nearby_trucks = FoodTruck.objects.with_rating_summary()
        open_only = request.query_params.get(
            "open_only", "").lower() in ("1", "true", "yes")
        if open_only:
            # currently_open also drops trucks whose closing time has passed
            nearby_trucks = nearby_trucks.currently_open()

        nearby_trucks = (
            nearby_trucks
            # dwithin on a geography field uses PostGIS ST_DWithin (index-backed)
            .filter(location__dwithin=(user_point, D(mi=radius_miles)))
            .annotate(distance_from_user=Distance("location", user_point))
            .order_by("distance_from_user")
        )

        serializer = self.get_serializer(
            nearby_trucks[:MAXIMUM_NEARBY_RESULTS], many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def mine(self, request):
        """GET /api/trucks/mine/ -- staff see every truck, owners see their own."""
        if request.user.is_staff:
            my_trucks = FoodTruck.objects.all()
        else:
            my_trucks = FoodTruck.objects.filter(owner=request.user)
        serializer = self.get_serializer(my_trucks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        """
        POST /api/trucks/<id>/check-in/
        {"latitude": 34.05, "longitude": -117.18, "open_until": "2026-11-15T22:00:00Z"}
        """
        # get_object runs IsOwnerOrStaffOrReadOnly.has_object_permission
        food_truck = self.get_object()
        check_in_serializer = CheckInSerializer(data=request.data)
        check_in_serializer.is_valid(raise_exception=True)
        check_in_data = check_in_serializer.validated_data

        food_truck.location = Point(
            check_in_data["longitude"], check_in_data["latitude"], srid=4326)
        food_truck.open_until = check_in_data["open_until"]
        food_truck.is_open = True
        food_truck.save()
        return Response(self.get_serializer(food_truck).data)

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        """POST /api/trucks/<id>/check-out/ -- closes the truck immediately."""
        food_truck = self.get_object()
        food_truck.is_open = False
        food_truck.open_until = None
        food_truck.save()
        return Response(self.get_serializer(food_truck).data)

    @action(detail=True, methods=["get", "post"], url_path="reviews")
    def reviews(self, request, pk=None):
        """
        GET  /api/trucks/<id>/reviews/  -- list all reviews for this truck
        POST /api/trucks/<id>/reviews/  -- logged-in user posts or updates a review
        """
        food_truck = self.get_object()

        if request.method == "GET":
            truck_reviews = food_truck.reviews.select_related("user").all()
            serializer = ReviewSerializer(truck_reviews, many=True)
            return Response(serializer.data)

        if not request.user.is_authenticated:
            return Response(
                {"detail": "Please log in to leave a review."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if food_truck.owner_id == request.user.id:
            return Response(
                {"detail": "Truck owners cannot review their own food truck."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review, created = Review.objects.update_or_create(
            truck=food_truck,
            user=request.user,
            defaults=serializer.validated_data,
        )
        output_serializer = ReviewSerializer(review)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"reviews/(?P<review_id>[^/.]+)",
        permission_classes=[IsAuthenticated],
    )
    def review_detail(self, request, pk=None, review_id=None):
        """
        PATCH  /api/trucks/<id>/reviews/<review_id>/ -- edit own review
        DELETE /api/trucks/<id>/reviews/<review_id>/ -- delete own review
        """
        food_truck = self.get_object()
        review = food_truck.reviews.filter(pk=review_id).first()
        if review is None:
            return Response(
                {"detail": "Review not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not (request.user.is_staff or review.user_id == request.user.id):
            return Response(
                {"detail": "You can only modify your own review."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == "DELETE":
            review.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = ReviewSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
