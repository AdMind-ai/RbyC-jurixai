from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models.company_info.company_info import CompanyInfo


class CustomUser(AbstractUser):
    company = models.ForeignKey(
        CompanyInfo,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users"
    )
    is_company_admin = models.BooleanField(default=False)
    modified_at = models.DateTimeField(auto_now=True)
