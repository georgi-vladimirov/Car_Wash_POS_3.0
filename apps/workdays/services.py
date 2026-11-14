"""Business logic for opening and closing a work day.

Views call these functions and never change WorkDay directly, so every rule
(permissions, one open day per location, frozen balances) lives in one place.
Errors are raised as ValidationError (shown to the user in the form) or
PermissionDenied (403).
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Location

from .models import WorkDay


def _check_location_access(user: User, location_id: int) -> None:
    if not user.allowed_locations().filter(pk=location_id).exists():
        raise PermissionDenied("Нямате достъп до тази локация.")


def calculate_expected_balance(workday: WorkDay) -> Decimal:
    """Cash that should be in the drawer at the end of the day.

    TODO: add cash sales (sales), subtract expenses (expenses) and apply
    cash movements (cashbook) once those apps exist.
    """
    return workday.opening_balance


@transaction.atomic
def open_workday(*, user: User, location: Location, opening_balance: Decimal) -> WorkDay:
    """Open today's work day for a location. The date is always set by the server."""
    _check_location_access(user, location.pk)

    if opening_balance < 0:
        raise ValidationError("Началното салдо не може да е отрицателно.")

    # Lock the location row: two cashiers clicking "open" at the same time
    # are processed one after another, so the checks below stay valid.
    try:
        location = Location.objects.select_for_update().get(pk=location.pk)
    except Location.DoesNotExist:
        raise ValidationError("Локацията е неактивна.")

    today = timezone.localdate()
    days = WorkDay.objects.filter(location=location)

    if days.filter(closed_at__isnull=True).exists():
        raise ValidationError("Локацията вече има отворен ден. Първо го приключете.")
    if days.filter(date=today).exists():
        raise ValidationError("За днес вече има работен ден за тази локация.")

    return WorkDay.objects.create(
        location=location,
        date=today,
        opening_balance=opening_balance,
        opened_by=user,
    )


@transaction.atomic
def close_workday(
    *, user: User, workday: WorkDay, closing_balance: Decimal, difference_note: str = ""
) -> WorkDay:
    """Close a work day with the counted cash. Expected balance and difference are frozen.

    A difference (shortage or surplus) is allowed and recorded, but needs a note.
    """
    # Re-read and lock the row: the instance passed in may be stale
    # (e.g. the day was closed in another tab a moment ago).
    workday = WorkDay.objects.select_for_update().get(pk=workday.pk)

    _check_location_access(user, workday.location_id)

    if workday.is_closed:
        raise ValidationError("Денят вече е приключен.")
    if closing_balance < 0:
        raise ValidationError("Крайното салдо не може да е отрицателно.")

    expected_balance = calculate_expected_balance(workday)
    difference = closing_balance - expected_balance
    difference_note = (difference_note or "").strip()

    if difference != 0 and not difference_note:
        raise ValidationError("При разлика между очакваното и преброеното салдо бележката е задължителна.")

    workday.expected_balance = expected_balance
    workday.closing_balance = closing_balance
    workday.difference = difference
    workday.difference_note = difference_note
    workday.closed_by = user
    workday.closed_at = timezone.now()
    workday.save(
        update_fields=[
            "expected_balance",
            "closing_balance",
            "difference",
            "difference_note",
            "closed_by",
            "closed_at",
        ]
    )
    return workday
