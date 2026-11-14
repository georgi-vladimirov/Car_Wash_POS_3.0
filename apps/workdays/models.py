from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class WorkDay(models.Model):
    location = models.ForeignKey("core.Location", on_delete=models.PROTECT, verbose_name="Локация")
    location_id: int  # set by Django from the FK; declared for the type checker
    date = models.DateField("Дата")
    opening_balance = models.DecimalField("Начално салдо", max_digits=10, decimal_places=2)
    closing_balance = models.DecimalField("Крайно салдо", max_digits=10, decimal_places=2,
        null=True, blank=True)
    expected_balance = models.DecimalField("Очаквано салдо", max_digits=10, decimal_places=2,
        null=True, blank=True)
    difference = models.DecimalField("Разлика", max_digits=10, decimal_places=2,
        null=True, blank=True)
    difference_note = models.CharField("Бележка при разлика", max_length=200, blank=True)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="opened_workdays", verbose_name="Отворил")
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="closed_workdays",
        verbose_name="Приключил")
    opened_at = models.DateTimeField("Отворен на", auto_now_add=True)
    closed_at = models.DateTimeField("Приключен на", null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self) -> str:
        return f"{self.location.short_name} · {self.date:%d.%m.%Y}"

    @property
    def is_closed(self):
        return self.closed_at is not None

    class Meta:
        verbose_name = "Работен ден"
        verbose_name_plural = "Работни дни"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "date"],
                name="unique_workday_per_location_date",
                violation_error_message="За тази локация вече има работен ден на тази дата.",
            ),
            models.UniqueConstraint(
                fields=["location"],
                condition=models.Q(closed_at__isnull=True),
                name="one_open_workday_per_location",
                violation_error_message="Локацията вече има отворен ден.",
            ),
            models.CheckConstraint(
                condition=models.Q(opening_balance__gte=0),
                name="workday_opening_balance_non_negative",
                violation_error_message="Началното салдо не може да е отрицателно.",
            ),
            models.CheckConstraint(
                condition=models.Q(closing_balance__isnull=True)
                | models.Q(closing_balance__gte=0),
                name="workday_closing_balance_non_negative",
                violation_error_message="Крайното салдо не може да е отрицателно.",
            ),
            # Closing fields are either all empty (open day) or all filled (closed day)
            models.CheckConstraint(
                condition=models.Q(
                    closed_at__isnull=True,
                    closed_by__isnull=True,
                    closing_balance__isnull=True,
                    expected_balance__isnull=True,
                    difference__isnull=True,
                )
                | models.Q(
                    closed_at__isnull=False,
                    closed_by__isnull=False,
                    closing_balance__isnull=False,
                    expected_balance__isnull=False,
                    difference__isnull=False,
                ),
                name="workday_closing_fields_consistent",
                violation_error_message="При приключване трябва да има час, потребител и крайно салдо.",
            ),
        ]
