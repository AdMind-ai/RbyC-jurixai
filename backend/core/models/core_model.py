from django.db import models


class CoreModel(models.Model):
    """
    Modelo base para armazenar dados principais da aplicação.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Core Model"
        verbose_name_plural = "Core Models"

    def __str__(self):
        return self.name
