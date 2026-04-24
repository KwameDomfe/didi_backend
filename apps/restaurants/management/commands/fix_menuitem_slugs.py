from django.core.management.base import BaseCommand
from restaurants.models import MenuItem
from collections import defaultdict

class Command(BaseCommand):
    help = "Fix duplicate MenuItem slugs by regenerating them."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Checking for duplicate MenuItem slugs..."))
        menuitem_slugs = defaultdict(list)
        for m in MenuItem.objects.all():
            menuitem_slugs[m.slug].append(m)
        duplicates = {s: items for s, items in menuitem_slugs.items() if len(items) > 1}
        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No duplicate MenuItem slugs found."))
            return
        self.stdout.write(self.style.ERROR(f"Found {len(duplicates)} duplicate slugs. Fixing..."))
        fixed_count = 0
        for slug, items in duplicates.items():
            # Keep the first, fix the rest
            for item in items[1:]:
                old_slug = item.slug
                item.slug = ''  # Clear slug to force regeneration
                item.save()
                self.stdout.write(f"  Fixed MenuItem id={item.id}: '{old_slug}' -> '{item.slug}'")
                fixed_count += 1
        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} duplicate MenuItem slugs."))
