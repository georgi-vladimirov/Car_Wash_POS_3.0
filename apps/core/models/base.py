from typing import TypeVar

from django.db import models

_T = TypeVar("_T", bound=models.Model)

class ActiveManager(models.Manager[_T]):
     def get_queryset(self) -> models.QuerySet[_T]:
        return super().get_queryset().filter(is_active=True)

class BaseModel(models.Model):
    """
    Abstract base model providing common fields and utilities for all models.
    """
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True  # This makes it an abstract base class and won't create a separate DB table
        

