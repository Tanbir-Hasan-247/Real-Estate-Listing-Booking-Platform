from django.core.management.base import BaseCommand

from users.demo_accounts import DEMO_ACCOUNTS, ensure_demo_accounts


class Command(BaseCommand):
    help = "Create or refresh showcase Demo Admin, Agent, and Client accounts with sample workspace activity."

    def handle(self, *args, **options):
        accounts = ensure_demo_accounts(seed_activity=True)
        self.stdout.write(self.style.SUCCESS("PropNest showcase demo accounts ready:"))
        for spec in DEMO_ACCOUNTS:
            user = accounts[spec["key"]]
            self.stdout.write(
                f"  - {spec['label']}: username={user.username} password={spec['password']} (role={user.role}, active={user.is_active})"
            )
