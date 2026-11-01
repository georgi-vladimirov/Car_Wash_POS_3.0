from django.db import models

from .base import BaseModel


class Location(BaseModel):
    name = models.CharField("Име", max_length=100, unique=True)
    short_name = models.CharField("Код", max_length=4, unique=True)

    ################
    def __str__(self) -> str:
        return f"{self.name} - {self.short_name}"

    class Meta(BaseModel.Meta):
        verbose_name = "Локация"
        verbose_name_plural = "Локации"
