from rest_framework import serializers
from core.models.saved_newsletter_model import SavedNewsletter, NewsletterType, NewsletterSource


class SavedNewsletterSerializer(serializers.ModelSerializer):
    newsletter_type_display = serializers.CharField(source="get_newsletter_type_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = SavedNewsletter
        fields = [
            "id",
            "title",
            "content",
            "newsletter_type",
            "newsletter_type_display",
            "source",
            "source_display",
            "metadata",
            "generated_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "newsletter_type_display", "source_display"]


class SavedNewsletterListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (no full content)."""
    newsletter_type_display = serializers.CharField(source="get_newsletter_type_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    preview = serializers.SerializerMethodField()

    class Meta:
        model = SavedNewsletter
        fields = [
            "id",
            "title",
            "newsletter_type",
            "newsletter_type_display",
            "source",
            "source_display",
            "preview",
            "generated_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_preview(self, obj):
        """First 160 chars of content as preview."""
        return obj.content[:160].strip() + ("…" if len(obj.content) > 160 else "")


class SaveNewsletterSerializer(serializers.Serializer):
    """Used when the frontend saves a manually-created newsletter."""
    title = serializers.CharField(max_length=512, required=False, allow_blank=True)
    content = serializers.CharField()
    metadata = serializers.JSONField(required=False)
    newsletter_type = serializers.ChoiceField(
        choices=NewsletterType.choices,
        default=NewsletterType.NEWSLETTER,
    )

    def create(self, validated_data):
        content = validated_data["content"]
        title = validated_data.get("title", "").strip()
        if not title:
            # Auto-generate title from first non-empty line
            first_line = next((l.strip().lstrip("#").strip() for l in content.splitlines() if l.strip()), "")
            title = first_line[:120] if first_line else "Newsletter senza titolo"
        return SavedNewsletter.objects.create(
            title=title,
            content=content,
            newsletter_type=validated_data.get("newsletter_type", NewsletterType.NEWSLETTER),
            source=NewsletterSource.MANUAL,
            metadata=validated_data.get("metadata") or {},
        )

