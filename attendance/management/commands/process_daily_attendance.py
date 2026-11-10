import logging
import time
from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from attendance.services import process_daily_attendance


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process missing student and employee attendance for a working day."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="attendance_date",
            help="Process a date in YYYY-MM-DD format; defaults to the local date.",
        )

    def handle(self, *args, **options):
        raw_date = options.get("attendance_date")
        if raw_date:
            try:
                attendance_date = date.fromisoformat(raw_date)
            except ValueError as exc:
                raise CommandError("--date must use YYYY-MM-DD format.") from exc
        else:
            attendance_date = timezone.localdate()

        today = timezone.localdate()
        if attendance_date > today:
            raise CommandError("Future attendance dates cannot be processed.")

        if attendance_date == today:
            cutoff = datetime.strptime(
                getattr(settings, "ATTENDANCE_AUTO_PROCESS_TIME", "18:00"),
                "%H:%M",
            ).time()
            if timezone.localtime().time() < cutoff:
                raise CommandError(
                    f"Today's attendance can be processed after {cutoff:%H:%M} "
                    f"({timezone.get_current_timezone_name()})."
                )

        started = time.perf_counter()
        logger.info("Daily attendance command started for %s.", attendance_date)
        try:
            result = process_daily_attendance(attendance_date)
        except Exception as exc:
            logger.exception(
                "Daily attendance processing failed for %s.",
                attendance_date,
            )
            raise CommandError("Daily attendance processing failed.") from exc

        duration = round(time.perf_counter() - started, 3)
        result["duration_seconds"] = duration
        logger.info("Daily attendance command completed: %s", result)
        self.stdout.write(self.style.SUCCESS(str(result)))
        if result["errors"]:
            raise CommandError(
                f"Completed with {result['errors']} processing error(s); see logs."
            )
