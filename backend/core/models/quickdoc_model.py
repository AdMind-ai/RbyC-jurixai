from django.db import models


class GeneratedDocument(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField(auto_now_add=True)
    doc_format = models.CharField(max_length=64)
    language = models.CharField(max_length=64)
    text = models.TextField()
    pdf_file = models.FileField(upload_to='documents/', null=True, blank=True)
    word_file = models.FileField(upload_to='documents/', null=True, blank=True)
