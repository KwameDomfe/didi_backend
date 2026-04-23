from django.core.management.base import BaseCommand
from accounts.models import CustomUser

class Command(BaseCommand):
    help = 'Delete all user accounts'

    def handle(self, *args, **kwargs):
        count = CustomUser.objects.count()
        CustomUser.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} user accounts."))
