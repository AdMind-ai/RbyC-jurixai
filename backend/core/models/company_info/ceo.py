from django.db import models
from core.models.company_info import CompanyInfo


class CEO(models.Model):
    company = models.ForeignKey(
        CompanyInfo, related_name='ceos', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.name} ({self.role})"
