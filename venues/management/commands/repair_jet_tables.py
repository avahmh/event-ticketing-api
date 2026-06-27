from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = (
        "Drop jet_* and dashboard_* tables, remove jet/dashboard rows from django_migrations, "
        "then migrate again. Use when Jet raises missing column errors (e.g. user_id on "
        "jet_pinnedapplication)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Perform the destructive reset (required).",
        )

    def handle(self, *args, **options):
        if not options["reset"]:
            raise CommandError(
                "Refusing to run without --reset. Jet-only bookmarks/pins/dashboard layout "
                "will be removed."
            )
        if connection.vendor != "postgresql":
            raise CommandError("Only PostgreSQL is supported.")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                  AND (tablename LIKE %s OR tablename LIKE %s)
                ORDER BY tablename
                """,
                ["jet%", "dashboard%"],
            )
            tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            self.stdout.write("No jet_* or dashboard_* tables found; running migrate only.")
        else:
            with connection.cursor() as cursor:
                for name in tables:
                    qn = connection.ops.quote_name(name)
                    cursor.execute(f"DROP TABLE IF EXISTS {qn} CASCADE")
                    self.stdout.write(self.style.WARNING(f"Dropped {name}"))

        deleted, _ = MigrationRecorder.Migration.objects.filter(
            app__in=["jet", "dashboard"]
        ).delete()
        self.stdout.write(self.style.WARNING(f"Removed {deleted} django_migrations row(s) for jet/dashboard."))

        call_command("migrate", interactive=False, verbosity=1)
        self.stdout.write(self.style.SUCCESS("Migrate finished. Open /admin/ again."))
