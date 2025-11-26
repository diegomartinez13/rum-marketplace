from django.core.management.base import BaseCommand
from django.utils import timezone

from store_app.models import UserProfile


class Command(BaseCommand):
    help = (
        "Delete accounts that are still pending email verification and whose token has expired. "
        "Run periodically (e.g., daily via cron)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List accounts that would be deleted without deleting them.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Max accounts to delete in one run (default: 500).",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        qs = UserProfile.objects.select_related("user").filter(
            pending_email_verification=True,
            email_token_expires_at__isnull=False,
            email_token_expires_at__lt=now,
        ).order_by("email_token_expires_at")[: options["limit"]]

        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No expired unverified accounts found."))
            return

        self.stdout.write(f"Found {count} expired unverified account(s).")
        for profile in qs:
            self.stdout.write(
                f"- {profile.user.email} (expires: {profile.email_token_expires_at}, id={profile.user.id})"
            )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run enabled; no accounts deleted."))
            return

        deleted = 0
        for profile in qs:
            email = profile.user.email
            user_id = profile.user.id
            profile.user.delete()
            deleted += 1
            self.stdout.write(f"Deleted user {email} (id={user_id})")

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired unverified account(s)."))
