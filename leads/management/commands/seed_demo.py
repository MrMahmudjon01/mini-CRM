import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from leads.models import Activity, Lead

NAMES = ["Aziz Karimov", "Dilnoza Rahimova", "Jasur Tursunov", "Malika Yusupova",
         "Sardor Abdullayev", "Nigora Ismoilova", "Bekzod Umarov", "Madina Saidova",
         "Otabek Nazarov", "Zarina Qodirova", "Rustam Aliyev", "Sevara Mirzaeva"]


class Command(BaseCommand):
    help = "Create a demo user (demo / demo12345) with sample leads."

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
        if created:
            user.set_password("demo12345")
            user.save()
        if user.leads.exists():
            self.stdout.write("Demo data already present.")
            return
        rng = random.Random(1)
        for i, name in enumerate(NAMES):
            lead = Lead.objects.create(
                owner=user, name=name,
                phone=f"+99890{rng.randint(1000000, 9999999)}",
                email=f"{name.split()[0].lower()}@example.com" if i % 2 == 0 else "",
                source=rng.choice(Lead.Source.values),
                status=rng.choice(Lead.Status.values),
                note="Interested in our service." if i % 3 == 0 else "",
            )
            Activity.objects.create(lead=lead, actor=user, action=Activity.Action.CREATED,
                                    message=f"Lead created with status {lead.get_status_display()}")
        self.stdout.write(self.style.SUCCESS("Created demo user demo / demo12345 with 12 leads."))
