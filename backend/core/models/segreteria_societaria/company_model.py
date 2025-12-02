from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class Company(models.Model):
    class CompanyType(models.TextChoices):
        SRL = 'S.r.l.', 'S.r.l.'
        SPA = 'S.p.A.', 'S.p.A.'
        SAPAA = 'S.a.p.a.', 'S.a.p.a.'
        SRLS = 'S.r.l.s.', 'S.r.l.s.'

    class Status(models.TextChoices):
        ACTIVE = 'Active', _('Attiva')
        LIQUIDATION = 'Liquidation', _('In Liquidazione')
        INACTIVE = 'Inactive', _('Inattiva')

    name = models.CharField(max_length=255, verbose_name=_("Ragione Sociale"))
    # Make VAT number optional for initial creation (only name required)
    vat_number = models.CharField(max_length=50, unique=False, null=True, blank=True, verbose_name=_("Partita IVA"))
    company_type = models.CharField(
        max_length=20, 
        choices=CompanyType.choices, 
        default=CompanyType.SRL,
        verbose_name=_("Tipo Società")
    )
    address = models.TextField(null=True, blank=True, verbose_name=_("Sede Legale"))
    capital = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
        verbose_name=_("Capitale Sociale")
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.ACTIVE,
        verbose_name=_("Stato")
    )
    next_meeting_date = models.DateField(null=True, blank=True, verbose_name=_("Prossima Assemblea"))
    
    # Campos para Carta Intestata (Letterhead)
    letterhead_info = models.TextField(null=True, blank=True, verbose_name=_("Testo Intestazione"))
    letterhead_file = models.FileField(upload_to='letterheads/', null=True, blank=True, verbose_name=_("File Intestazione"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Società")
        verbose_name_plural = _("Società")

    def __str__(self):
        return self.name