from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, Q
from django.utils import timezone


class FoodTruckQuerySet(models.QuerySet):
    def currently_open(self):
        """
        Trucks that are open right now: marked open AND either no closing
        time was given or the closing time hasn't passed yet. A truck whose
        owner forgot to check out closes on its own at open_until.
        """
        return self.filter(is_open=True).filter(
            Q(open_until__isnull=True) | Q(open_until__gt=timezone.now())
        )

    def with_rating_summary(self):
        return self.annotate(
            average_rating=Avg("reviews__rating"),
            review_count=Count("reviews", distinct=True),
        )


class FoodTruck(models.Model):
    """A food truck and where it is parked right now."""

    name = models.CharField(max_length=120)
    cuisine = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)

    # geography=True stores the point on the earth's surface, so distance
    # lookups are calculated in meters instead of degrees.
    # srid=4326 is plain longitude/latitude (what phones and Leaflet use).
    location = gis_models.PointField(geography=True, srid=4326)

    is_open = models.BooleanField(default=False)
    # Set by the owner at check-in; after this time the truck counts as closed
    open_until = models.DateTimeField(null=True, blank=True)

    # The truck owner's login; only they (or staff) can move the truck.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="food_trucks",
    )

    location_updated_at = models.DateTimeField(auto_now=True)

    objects = FoodTruckQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_currently_open(self):
        """Same rule as FoodTruckQuerySet.currently_open, for a single truck."""
        if not self.is_open:
            return False
        return self.open_until is None or self.open_until > timezone.now()


class Review(models.Model):

    truck = models.ForeignKey(
        FoodTruck,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="truck_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    photo_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["truck", "user"],
                name="unique_review_per_user_per_truck",
            )
        ]

    def __str__(self):
        return f"{self.truck.name} - {self.rating}★ by {self.user.username}"
