from rest_framework import serializers

LANGUAGES = {
    'english': 'english',
    'french': 'french',
    'german': 'german',
    'greek': 'greek',
    'italian': 'italian',
    'portuguese': 'portuguese',
    'spanish': 'spanish',
}

LANGUAGE_CHOICES = [(code, language.title())
                    for language, code in LANGUAGES.items()]


class TranslateFileSerializer(serializers.Serializer):
    file = serializers.FileField()
    origin = serializers.ChoiceField(choices=LANGUAGE_CHOICES)
    target = serializers.ChoiceField(choices=LANGUAGE_CHOICES)
