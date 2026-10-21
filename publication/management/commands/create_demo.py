"""Create the demo café for reviewers: one owner, one kitchen and one service account with example data.

The password comes from the environment variable DJANGO_DEMO_PASSWORD, so it is never stored in the
repository. Without it the command does nothing. Running it again changes nothing that already exists.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Business, Membership, Role
from publication.services import sync
from recipes.example_data import load_example_data

BUSINESS_NAME = "Café Demo"
# example.com is reserved for examples (RFC 2606), so no real person receives mail for these accounts.
ACCOUNTS = [
    ("demo-owner@example.com", Role.OWNER),
    ("demo-kitchen@example.com", Role.KITCHEN),
    ("demo-service@example.com", Role.SERVICE),
]


class Command(BaseCommand):
    help = "Create the demo café with three accounts (password from DJANGO_DEMO_PASSWORD)."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("DJANGO_DEMO_PASSWORD", "")
        if not password:
            self.stdout.write("DJANGO_DEMO_PASSWORD is not set, no demo café created.")
            return
        owner = get_user_model().objects.filter(username=ACCOUNTS[0][0]).select_related("membership").first()
        if owner:
            # Calculate again, so the guest menu is right even for a demo café made by an older version.
            sync(owner.membership.business)
            self.stdout.write("Demo café already exists.")
            return
        business = Business.objects.create(name=BUSINESS_NAME)
        for email, role in ACCOUNTS:
            user = get_user_model().objects.create_user(username=email, email=email, password=password)
            Membership.objects.create(user=user, business=business, role=role)
        ingredients, recipes = load_example_data(business)
        sync(business)  # publish the declarations, as a saved change in the app would
        self.stdout.write(f"Demo café created with {ingredients} ingredients and {recipes} recipes.")
