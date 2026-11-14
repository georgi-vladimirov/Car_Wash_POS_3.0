from apps.core.models import Location

from .models import WorkDay


def get_last_closed_workday(location: Location) -> WorkDay | None:
    """Most recent closed work day of a location, or None if there is none."""
    return (
        WorkDay.objects
        .filter(location=location,  closed_at__isnull=False)
        .order_by("-date")
        .first()
    )