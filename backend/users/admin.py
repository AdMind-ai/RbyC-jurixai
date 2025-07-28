from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informazioni Azienda', {'fields': ('company', 'is_company_admin')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informazioni Azienda', {'fields': ('company', 'is_company_admin')}),
    )
    list_display = UserAdmin.list_display + ('company', 'is_company_admin')
    list_filter = UserAdmin.list_filter + ('company', 'is_company_admin')
