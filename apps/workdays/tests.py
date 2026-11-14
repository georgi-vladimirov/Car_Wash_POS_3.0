from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Location

from .models import WorkDay
from .selectors import get_last_closed_workday
from .services import close_workday, open_workday


class WorkDayTestCase(TestCase):
    """Shared fixtures: two locations, a cashier for each, and an owner."""

    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.create(name="Център", short_name="CEN")
        cls.other_location = Location.objects.create(name="Изток", short_name="EST")
        cls.cashier = User.objects.create_user(
            username="cashier", password="test-pass-123", location=cls.location
        )
        cls.other_cashier = User.objects.create_user(
            username="other", password="test-pass-123", location=cls.other_location
        )
        cls.owner = User.objects.create_user(
            username="owner", password="test-pass-123", role=User.Role.OWNER
        )

    def create_closed_day(self, location, day, closing_balance=Decimal("100.00")):
        """Insert a closed day directly (bypasses the services) for selector tests."""
        return WorkDay.objects.create(
            location=location,
            date=day,
            opening_balance=Decimal("100.00"),
            opened_by=self.cashier,
            expected_balance=Decimal("100.00"),
            closing_balance=closing_balance,
            difference=closing_balance - Decimal("100.00"),
            closed_by=self.cashier,
            closed_at=timezone.now(),
        )


class OpenWorkdayTests(WorkDayTestCase):
    def test_opens_today_with_server_date(self):
        workday = open_workday(
            user=self.cashier, location=self.location, opening_balance=Decimal("150.00")
        )

        self.assertEqual(workday.date, timezone.localdate())
        self.assertEqual(workday.opening_balance, Decimal("150.00"))
        self.assertEqual(workday.opened_by, self.cashier)
        self.assertIsNotNone(workday.opened_at)
        self.assertFalse(workday.is_closed)

    def test_cannot_open_second_day_while_one_is_open(self):
        open_workday(user=self.cashier, location=self.location, opening_balance=Decimal(0))

        with self.assertRaisesMessage(ValidationError, "вече има отворен ден"):
            open_workday(user=self.cashier, location=self.location, opening_balance=Decimal(0))

        self.assertEqual(WorkDay.objects.count(), 1)

    def test_cannot_open_same_date_twice_after_closing(self):
        workday = open_workday(
            user=self.cashier, location=self.location, opening_balance=Decimal(0)
        )
        close_workday(user=self.cashier, workday=workday, closing_balance=Decimal(0))

        with self.assertRaisesMessage(ValidationError, "За днес вече има работен ден"):
            open_workday(user=self.cashier, location=self.location, opening_balance=Decimal(0))

    def test_open_day_in_one_location_does_not_block_another(self):
        open_workday(user=self.owner, location=self.location, opening_balance=Decimal(0))
        open_workday(user=self.owner, location=self.other_location, opening_balance=Decimal(0))

        self.assertEqual(WorkDay.objects.count(), 2)

    def test_cashier_cannot_open_day_in_other_location(self):
        with self.assertRaises(PermissionDenied):
            open_workday(
                user=self.cashier, location=self.other_location, opening_balance=Decimal(0)
            )

        self.assertFalse(WorkDay.objects.exists())

    def test_owner_can_open_day_in_any_location(self):
        workday = open_workday(
            user=self.owner, location=self.other_location, opening_balance=Decimal(0)
        )

        self.assertEqual(workday.location, self.other_location)

    def test_negative_opening_balance_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, "не може да е отрицателно"):
            open_workday(
                user=self.cashier, location=self.location, opening_balance=Decimal("-0.01")
            )

    def test_cannot_open_day_in_inactive_location(self):
        self.location.is_active = False
        self.location.save()

        # Owner, so the access check passes and the inactive-location rule is tested
        with self.assertRaises((ValidationError, PermissionDenied)):
            open_workday(user=self.owner, location=self.location, opening_balance=Decimal(0))

        self.assertFalse(WorkDay.objects.exists())


class CloseWorkdayTests(WorkDayTestCase):
    def setUp(self):
        self.workday = open_workday(
            user=self.cashier, location=self.location, opening_balance=Decimal("100.00")
        )

    def test_close_without_difference_freezes_balances(self):
        workday = close_workday(
            user=self.cashier, workday=self.workday, closing_balance=Decimal("100.00")
        )

        workday.refresh_from_db()
        self.assertTrue(workday.is_closed)
        self.assertEqual(workday.expected_balance, Decimal("100.00"))
        self.assertEqual(workday.closing_balance, Decimal("100.00"))
        self.assertEqual(workday.difference, Decimal("0.00"))
        self.assertEqual(workday.difference_note, "")
        self.assertEqual(workday.closed_by, self.cashier)

    def test_shortage_without_note_is_rejected_and_day_stays_open(self):
        with self.assertRaisesMessage(ValidationError, "бележката е задължителна"):
            close_workday(
                user=self.cashier, workday=self.workday, closing_balance=Decimal("90.00")
            )

        self.workday.refresh_from_db()
        self.assertFalse(self.workday.is_closed)

    def test_whitespace_only_note_counts_as_missing(self):
        with self.assertRaisesMessage(ValidationError, "бележката е задължителна"):
            close_workday(
                user=self.cashier,
                workday=self.workday,
                closing_balance=Decimal("90.00"),
                difference_note="   ",
            )

    def test_shortage_with_note_is_recorded(self):
        workday = close_workday(
            user=self.cashier,
            workday=self.workday,
            closing_balance=Decimal("90.00"),
            difference_note="  Грешно ресто  ",
        )

        workday.refresh_from_db()
        self.assertTrue(workday.is_closed)
        self.assertEqual(workday.difference, Decimal("-10.00"))
        self.assertEqual(workday.difference_note, "Грешно ресто")

    def test_surplus_with_note_is_recorded(self):
        workday = close_workday(
            user=self.cashier,
            workday=self.workday,
            closing_balance=Decimal("105.50"),
            difference_note="Неотчетен бакшиш",
        )

        self.assertEqual(workday.difference, Decimal("5.50"))

    def test_cannot_close_twice(self):
        close_workday(user=self.cashier, workday=self.workday, closing_balance=Decimal("100.00"))

        with self.assertRaisesMessage(ValidationError, "вече е приключен"):
            close_workday(
                user=self.cashier, workday=self.workday, closing_balance=Decimal("100.00")
            )

    def test_stale_instance_cannot_close_again(self):
        # Same day loaded in two tabs: the first tab closes it
        stale = WorkDay.objects.get(pk=self.workday.pk)
        close_workday(user=self.cashier, workday=self.workday, closing_balance=Decimal("100.00"))

        with self.assertRaisesMessage(ValidationError, "вече е приключен"):
            close_workday(user=self.cashier, workday=stale, closing_balance=Decimal("100.00"))

    def test_cashier_cannot_close_day_in_other_location(self):
        with self.assertRaises(PermissionDenied):
            close_workday(
                user=self.other_cashier, workday=self.workday, closing_balance=Decimal("100.00")
            )

        self.workday.refresh_from_db()
        self.assertFalse(self.workday.is_closed)

    def test_negative_closing_balance_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, "не може да е отрицателно"):
            close_workday(
                user=self.cashier, workday=self.workday, closing_balance=Decimal("-1.00")
            )

    def test_closing_records_history_entry(self):
        close_workday(user=self.cashier, workday=self.workday, closing_balance=Decimal("100.00"))

        latest = self.workday.history.first()
        self.assertEqual(latest.history_type, "~")
        self.assertIsNotNone(latest.closed_at)


class GetLastClosedWorkdayTests(WorkDayTestCase):
    def test_returns_none_when_no_closed_day(self):
        self.assertIsNone(get_last_closed_workday(self.location))

    def test_returns_most_recent_closed_day(self):
        today = timezone.localdate()
        self.create_closed_day(self.location, today - timedelta(days=3))
        latest = self.create_closed_day(self.location, today - timedelta(days=1))
        self.create_closed_day(self.location, today - timedelta(days=2))

        self.assertEqual(get_last_closed_workday(self.location), latest)

    def test_ignores_open_day(self):
        today = timezone.localdate()
        closed = self.create_closed_day(self.location, today - timedelta(days=1))
        open_workday(user=self.cashier, location=self.location, opening_balance=Decimal(0))

        self.assertEqual(get_last_closed_workday(self.location), closed)

    def test_ignores_other_locations(self):
        today = timezone.localdate()
        self.create_closed_day(self.other_location, today - timedelta(days=1))

        self.assertIsNone(get_last_closed_workday(self.location))
