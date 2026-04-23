from django.core.management.base import BaseCommand
from restaurants.models import Restaurant, MenuItem
from collections import defaultdict

class Command(BaseCommand):
    help = "Audit Restaurant and MenuItem slugs for potential collisions or length issues"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting slug audit..."))
        restaurant_slugs = defaultdict(list)
        for r in Restaurant.objects.all():
            restaurant_slugs[r.slug].append(r.id)
        duplicate_restaurant = {s: ids for s, ids in restaurant_slugs.items() if len(ids) > 1}
        if duplicate_restaurant:
            self.stdout.write(self.style.ERROR("Duplicate Restaurant slugs detected:"))
            for s, ids in duplicate_restaurant.items():
                self.stdout.write(f"  {s}: {ids}
")
        else:
            self.stdout.write(self.style.SUCCESS("No duplicate Restaurant slugs."))

        menuitem_slugs = defaultdict(list)
        for m in MenuItem.objects.all():
            menuitem_slugs[m.slug].append(m.id)
        duplicate_menuitem = {s: ids for s, ids in menuitem_slugs.items() if len(ids) > 1}
        if duplicate_menuitem:
            self.stdout.write(self.style.ERROR("Duplicate MenuItem slugs detected:"))
            for s, ids in duplicate_menuitem.items():
                self.stdout.write(f"  {s}: {ids}")
        else:
            self.stdout.write(self.style.SUCCESS("No duplicate MenuItem slugs."))

        long_restaurants = [r for r in Restaurant.objects.all() if len(r.slug) > 250]
        long_menuitems = [m for m in MenuItem.objects.all() if len(m.slug) > 250]
        if long_restaurants or long_menuitems:
            self.stdout.write(self.style.WARNING("Found slugs approaching max length:"))
            for r in long_restaurants:
                self.stdout.write(f"  Restaurant {r.id} slug length {len(r.slug)}")
            for m in long_menuitems:
                self.stdout.write(f"  MenuItem {m.id} slug length {len(m.slug)}")
        else:
            self.stdout.write(self.style.SUCCESS("No overly long slugs found."))

        self.stdout.write(self.style.SUCCESS("Slug audit complete."))
