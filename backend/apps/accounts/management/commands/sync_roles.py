"""
Sync role groups (idempotent). Run after deployments that change roles.
"""

from django.core.management.base import BaseCommand

from apps.accounts.roles import sync_roles


class Command(BaseCommand):
    help = "Create/sync role-based Django groups."

    def handle(self, *args, **options):
        result = sync_roles()
        for group_name, count in result.items():
            self.stdout.write(f"  {group_name}: {count} members")
        self.stdout.write(self.style.SUCCESS("✔ Roles synced."))
