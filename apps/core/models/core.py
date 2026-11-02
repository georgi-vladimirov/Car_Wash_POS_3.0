from decimal import Decimal

from django.db import models
from django.db.models.functions import Lower

from .base import BaseModel


class Location(BaseModel):
    name = models.CharField("Име", max_length=100, unique=True)
    short_name = models.CharField("Код", max_length=4, unique=True)

    def __str__(self) -> str:
        return f"{self.name} - {self.short_name}"

    class Meta(BaseModel.Meta):
        verbose_name = "Локация"
        verbose_name_plural = "Локации"


class VehicleCategory(BaseModel):
    name = models.CharField("Име",max_length=20, unique=True)

    def __str__(self) -> str:
        return self.name

    class Meta(BaseModel.Meta):
        verbose_name = "Вид автомобил"
        verbose_name_plural = "Вид автомобили"


class ServiceCategory(BaseModel):
    name = models.CharField("Име", max_length=50, unique=True)
    max_per_wash = models.PositiveSmallIntegerField(
        "Макс. услуги в обслужване",
        default=1,
        help_text="Колко услуги от тази категория може да се изберат за една кола.",
    )
    order = models.IntegerField(default=1)

    def __str__(self) -> str:
        return self.name

    class Meta(BaseModel.Meta):
        verbose_name = "Вид услуга"
        verbose_name_plural = "Вид услуги"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_per_wash__gte=1),
                name="service_category_max_per_wash_min_1",
                violation_error_message="Трябва да може да се избере поне 1 услуга.",
            ),
        ]


class Service(BaseModel):
    name = models.CharField("Име",max_length=200, unique=True)
    service_type = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name="services",
        blank=True,
        null=True,
    )
    description = models.TextField(blank=True)
    
    def __str__(self) -> str:
        return f"{self.name}"

    class Meta(BaseModel.Meta):
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"


class ServicePrice(BaseModel):
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="service_prices",
        verbose_name="Локация",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="service_prices",
        verbose_name="Услуга",
    )
    vehicle_category = models.ForeignKey(
        VehicleCategory, on_delete=models.CASCADE, verbose_name="Вид автомобил"
    )
    amount = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    valid_from = models.DateField("Валидна от")

    IMMUTABLE_FIELDS = {
        "location_id",
        "service_id",
        "vehicle_category_id",
        "amount",
        "valid_from",
    }

    def save(self, *args, **kwargs):
        if self.pk:
            original = ServicePrice.all_objects.get(pk=self.pk)
            changed = {
                f
                for f in self.IMMUTABLE_FIELDS
                if getattr(self, f) != getattr(original, f)
            }
            if changed:
                raise ValueError(
                    f"ServicePrice fields {changed} cannot be modified after creation."
                )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.service.name} - {self.vehicle_category.name} @ "
            f"{self.location.short_name}: {self.amount} (от {self.valid_from:%d.%m.%Y})"
        )

    class Meta(BaseModel.Meta):
        verbose_name = "Цена на услуга"
        verbose_name_plural = "Цени на услуги"
        get_latest_by = "valid_from"
        constraints = [
            models.UniqueConstraint(
                fields=["location", "service", "vehicle_category", "valid_from"],
                name="unique_service_price",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="service_price_amount_non_negative",
            ),
        ]


class VehicleBrand(BaseModel):
    brand = models.CharField(max_length=50, unique=True)
    number_sort = models.IntegerField()

    def __str__(self) -> str:
        return f"{self.brand}"

    class Meta(BaseModel.Meta):
        verbose_name = "Марка"
        verbose_name_plural = "Марки"


class EmployeePosition(BaseModel):
    position = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.position

    class Meta(BaseModel.Meta):
        verbose_name = "Длъжност"
        verbose_name_plural = "Длъжности"


class Employee(BaseModel):
    first_name = models.CharField("Име", max_length=50)
    last_name = models.CharField("Фамилия", max_length=50)
    short_name = models.CharField(
        "Кратко име",
        max_length=20,
        help_text="Уникално име, което се показва при избор на служител.",
    )
    position = models.ForeignKey(
        EmployeePosition, on_delete=models.PROTECT, related_name="employees"
    )
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="employees"
    )
    # Current rates only; the rate used is copied into the payroll record at calculation time
    salary_percentage = models.DecimalField(
        "Процент заплата",
        max_digits=5,
        decimal_places=2,
        default=Decimal(0),
        help_text="В проценти: 30 = 30%.",
    )
    bonus_percentage = models.DecimalField(
        "Процент бонус",
        max_digits=5,
        decimal_places=2,
        default=Decimal(0),
        help_text="В проценти: 5 = 5%.",
    )

    def clean(self):
        super().clean()
        self.short_name = self.short_name.strip()

    def __str__(self) -> str:
        return f"{self.short_name} ({self.first_name} {self.last_name})"

    class Meta(BaseModel.Meta):
        verbose_name = "Служител"
        verbose_name_plural = "Служители"
        constraints = [
            # Case-insensitive and also across inactive employees, so old reports stay unambiguous
            models.UniqueConstraint(
                Lower("short_name"), name="unique_employee_short_name_ci"
            ),
            models.CheckConstraint(
                condition=models.Q(salary_percentage__range=(0, 100)),
                name="employee_salary_percentage_0_100",
                violation_error_message="Процентът заплата трябва да е между 0 и 100.",
            ),
            models.CheckConstraint(
                condition=models.Q(bonus_percentage__range=(0, 100)),
                name="employee_bonus_percentage_0_100",
                violation_error_message="Процентът бонус трябва да е между 0 и 100.",
            ),
        ]


class Subscriber(BaseModel):
    name = models.CharField("Име", max_length=100, unique=True)
    company_id = models.CharField(max_length=13, unique=True)
    # Current discount only; the discount used is copied into the wash at sale time
    discount_percentage = models.DecimalField(
        "Отстъпка",
        max_digits=5,
        decimal_places=2,
        default=Decimal(0),
        help_text="В проценти: 10 = 10%.",
    )
    location = models.ManyToManyField(Location, related_name="subscribers")

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta(BaseModel.Meta):
        verbose_name = "Абонат"
        verbose_name_plural = "Абонати"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(discount_percentage__range=(0, 100)),
                name="subscriber_discount_percentage_0_100",
                violation_error_message="Отстъпката трябва да е между 0 и 100%.",
            ),
        ]