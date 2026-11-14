from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from simple_history.models import HistoricalRecords

from apps.core.models import Location


class AppUserManager(UserManager["User"]):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Superusers have no location, so they must be owners to pass the constraint
        extra_fields.setdefault("role", User.Role.OWNER)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CASHIER = "cashier", "Касиер"
        OWNER = "owner", "Собственик"

    role = models.CharField("Роля", max_length=10, choices=Role, default=Role.CASHIER)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Локация",
    )
    location_id: int | None  # set by Django from the FK; declared for the type checker

    objects = AppUserManager()
    history = HistoricalRecords(excluded_fields=["password", "last_login"])

    class Meta:
        verbose_name = "Потребител"
        verbose_name_plural = "Потребители"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role="owner") | models.Q(location__isnull=False),
                name="cashier_must_have_location",
                violation_error_message="Касиерът трябва да има локация.",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["cashier", "owner"]),
                name="user_role_valid",
                violation_error_message="Невалидна роля.",
            ),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def is_owner(self) -> bool:
        return self.role == self.Role.OWNER

    @property
    def is_cashier(self) -> bool:
        return self.role == self.Role.CASHIER

    def clean(self):
        super().clean()
        # Field-level error in forms; the DB constraint is the final guard
        if self.is_cashier and self.location_id is None:
            raise ValidationError({"location": "Касиерът трябва да има локация."})

    def allowed_locations(self, include_inactive: bool = False) -> QuerySet[Location]:
        """Single source of truth for the location filter mixin.

        include_inactive=True is for reports, so archived locations keep their history.
        """
        manager = Location.all_objects if include_inactive else Location.objects
        if self.is_owner:
            return manager.all()
        return manager.filter(pk=self.location_id)
