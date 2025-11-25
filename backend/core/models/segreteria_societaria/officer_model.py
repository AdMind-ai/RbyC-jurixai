from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models.segreteria_societaria.company_model import Company


class Officer(models.Model):
    """
    Representa os Órgãos Sociais (Amministratori, Sindaci, etc.)
    """
    class Role(models.TextChoices):
        AMM_UNICO = 'Amministratore Unico', _('Amministratore Unico')
        CONSIGLIERE = 'Consigliere', _('Consigliere')
        PRESIDENTE_CDA = 'Presidente CdA', _('Presidente CdA')
        SINDACO = 'Sindaco', _('Sindaco')
        REVISORE = 'Revisore', _('Revisore')

    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='officers',
        verbose_name=_("Società")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nome e Cognome"))
    role = models.CharField(max_length=50, choices=Role.choices, verbose_name=_("Carica"))
    appointed_date = models.DateField(verbose_name=_("Data Nomina"))
    expiry_date = models.DateField(null=True, blank=True, verbose_name=_("Data Scadenza"))

    class Meta:
        verbose_name = _("Carica Sociale")
        verbose_name_plural = _("Cariche Sociali")

    def __str__(self):
        return f"{self.name} ({self.role}) - {self.company.name}"