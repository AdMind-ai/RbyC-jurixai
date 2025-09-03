from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informazioni Azienda', {'fields': ('is_company_admin',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informazioni Azienda', {'fields': ('is_company_admin',)}),
    )
    list_display = UserAdmin.list_display + ('is_company_admin', "modified_at")
    list_filter = UserAdmin.list_filter + ('is_company_admin',)
    readonly_fields = UserAdmin.readonly_fields + ("modified_at",)
