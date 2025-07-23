from django.db import models


class CompanyInfo(models.Model):
    long_name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255)
    stock_symbol = models.CharField(max_length=32, unique=True)
    website = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    sector = models.CharField(max_length=128, blank=True)
    country = models.CharField(max_length=64, blank=True)
    state = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=64, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.long_name
