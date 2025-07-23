from django.db import models
from core.models.company_info import CompanyInfo


class CompetitorInfo(models.Model):
    company = models.ForeignKey(
        CompanyInfo, related_name='competitors_of', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    stock_symbol = models.CharField(max_length=32, blank=True)
    sector = models.CharField(max_length=128, blank=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.stock_symbol})"
