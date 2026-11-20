"""
Data migration: drops the "[Sample] " tag from seeded truck names.

Renames rows in place (same database row, same id), so reviews and cover
photos stay attached. Nothing is deleted. If a truck with the plain name
already exists, the tagged one is left alone instead of creating two
trucks with the same name.
"""

from django.db import migrations

OLD_SAMPLE_PREFIX = "[Sample] "


def remove_sample_prefix(apps, schema_editor):
    # Use the historical model, as Django requires inside migrations
    food_truck_model = apps.get_model("trucks", "FoodTruck")
    for tagged_truck in food_truck_model.objects.filter(name__startswith=OLD_SAMPLE_PREFIX):
        plain_name = tagged_truck.name[len(OLD_SAMPLE_PREFIX):]
        if food_truck_model.objects.filter(name=plain_name).exists():
            continue  # avoid a duplicate name; leave this row as it was
        tagged_truck.name = plain_name
        tagged_truck.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [
        ("trucks", "0004_foodtruck_cover_photo_url"),
    ]

    operations = [
        # Reversing does nothing: names stay plain, and no data is lost
        migrations.RunPython(remove_sample_prefix, migrations.RunPython.noop),
    ]
