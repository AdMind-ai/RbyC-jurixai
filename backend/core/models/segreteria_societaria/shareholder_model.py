from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from core.models.segreteria_societaria.company_model import Company


class Shareholder(models.Model):
    """
    Representa a Compagine Sociale (Sócios)
    """
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='shareholders',
        verbose_name=_("Società")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nome Socio"))
    quota_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Quota %")
    )

    class Meta:
        verbose_name = _("Socio")
        verbose_name_plural = _("Soci")

    def __str__(self):
        return f"{self.name} - {self.company.name}"