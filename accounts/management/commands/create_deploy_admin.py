
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the production administrator using environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not username or not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Admin environment variables not configured. Skipping."
                )
            )
            return

        User = get_user_model()

        existing_user = User.objects.filter(
            **{User.USERNAME_FIELD: username}
        ).first()

        if existing_user:
            if existing_user.is_superuser:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Superuser '{username}' already exists. No changes made."
                    )
                )
                return

            raise CommandError(
                f"Username '{username}' already exists but is not a superuser. "
                "Choose another username."
            )

        user = User(
            **{
                User.USERNAME_FIELD: username,
                "email": email,
            }
        )

        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Production superuser '{username}' created successfully."
            )
        )
