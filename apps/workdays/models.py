from core.models import BaseModel
from django.db import models

from config import settings


class WorkDay(BaseModel):
    location = models.ForeignKey("core.Location", on_delete=models.PROTECT)
    date = models.DateField("Дата")
    opening_balance = models.DecimalField("Начално салдо", max_digits=10, decimal_places=2)
    closing_balance = models.DecimalField("Крайно салдо", max_digits=10, decimal_places=2,
                                          null=True, blank=True)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  related_name="opened_workdays")
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  null=True, blank=True, related_name="closed_workdays")
    closed_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_closed(self):
        return self.closed_at is not None
