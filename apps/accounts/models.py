from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user; role and location will be added later."""
    pass
