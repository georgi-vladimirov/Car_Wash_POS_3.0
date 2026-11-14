from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AppUserAdmin(UserAdmin):
    list_display = ["username", "get_full_name", "role", "location", "is_active"]
    list_filter = ["role", "location", "is_active"]
    fieldsets = [
        *(UserAdmin.fieldsets or ()),
        ("Роля и локация", {"fields": ["role", "location"]}),
    ]
    add_fieldsets = [
        *UserAdmin.add_fieldsets,
        ("Роля и локация", {"fields": ["role", "location"]}),
    ]
