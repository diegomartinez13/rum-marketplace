from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from catalog.models import Category, Listing

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        U = get_user_model()
        u, _ = U.objects.get_or_create(username="vendor", defaults={"email":"v@x.com"})
        u.set_password("vendor"); u.is_vendor=True; u.save()
        names = ["Clothing","Video games","Technologies","Art","Books","Furniture","Housing","Food","Miscellaneous"]
        cats = [Category.objects.get_or_create(name=n)[0] for n in names]
        if not Listing.objects.exists():
            Listing.objects.create(title="Hoodie", price=50, category=cats[0], vendor=u, tags="green,rum")
            Listing.objects.create(title="Nintendo Switch", price=200, category=cats[1], vendor=u)
            Listing.objects.create(title="Landscape Painting", price=30, category=cats[3], vendor=u)
        self.stdout.write(self.style.SUCCESS("Seeded"))
