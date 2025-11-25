from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models.segreteria_societaria.company_model import Company


class Deadline(models.Model):
    """
    Representa as Scadenze (Prazos)
    """
    class Category(models.TextChoices):
        TAX = 'TAX', _('Fiscale')
        CORPORATE = 'CORPORATE', _('Societario')
        LEGAL = 'LEGAL', _('Legale')

    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='deadlines',
        verbose_name=_("Società")
    )
    title = models.CharField(max_length=255, verbose_name=_("Titolo"))
    due_date = models.DateField(verbose_name=_("Data Scadenza"))
    completed = models.BooleanField(default=False, verbose_name=_("Completata"))
    category = models.CharField(
        max_length=20, 
        choices=Category.choices, 
        default=Category.CORPORATE,
        verbose_name=_("Categoria")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Scadenza")
        verbose_name_plural = _("Scadenze")
        ordering = ['due_date']

    def __str__(self):
        return f"{self.title} - {self.due_date}"