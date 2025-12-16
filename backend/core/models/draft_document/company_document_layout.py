from django.db import models


class CompanyDocumentLayout(models.Model):
    name = models.CharField(max_length=255)
    letterhead_base64 = models.TextField(blank=True, null=True)
    # optional Word template stored as base64 (.docx)
    word_letterhead_base64 = models.TextField(blank=True, null=True)
    document_title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
