from rest_framework import serializers

LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('it', 'Italian'),
    ('fr', 'French'),
    ('de', 'German'),
    ('pt', 'Portuguese'),
    ('el', 'Greek'),
    ('es', 'Spanish'),
]

VOICE_CHOICES = [
    ('9BWtsMINqrJLrRacOk9x', 'Aria'),
    ('CwhRBWXzGAHq8TQ4Fs17', 'Roger'),
    ('EXAVITQu4vr4xnSDxMaL', 'Sarah'),
    ('FGY2WhTYpPnrIDTdsKH5', 'Laura'),
    ('IKne3meq5aSn9XLyUdCD', 'Charlie'),
    ('JBFqnCBsd6RMkjVDRZzb', 'George'),
    ('N2lVS1w4EtoT3dr4eOWO', 'Callum'),
    ('SAz9YHcvj6GT2YYXdXww', 'River'),
    ('TX3LPaxmHKxFdv7VOQHJ', 'Liam'),
    ('XB0fDUnXU5powFXDhCwa', 'Charlotte'),
    ('Xb7hH8MSUJpSbSDYk0k2', 'Alice'),
    ('XrExE9yKIg1WjnnlVkGX', 'Matilda'),
    ('bIHbv24MWmeRgasZH58o', 'Will'),
    ('cgSgspJ2msm6clMCkdW9', 'Jessica'),
    ('cjVigY5qzO86Huf0OWal', 'Eric'),
    ('iP95p4xoKVk53GoZ742B', 'Chris'),
    ('nPczCjzI2devNBz1zQrb', 'Brian'),
    ('onwK4e9ZLuTAKqWW03F9', 'Daniel'),
    ('pFZP5JQG7iQjIQuC4Bku', 'Lily'),
    ('pqHfZKP75CvOlQylNhV4', 'Bill'),
    ('13Cuh3NuYvWOVQtLbRN8', 'MarcoTrox - Italian Professional Voice Talent'),
    ('3DR8c2yd30eztg65o4jV', 'Aaron - AI & Tech News'),
    ('80lPKtzJMPh1vjYMUgwe', 'Benjamin - Criovozia'),
    ('AnvlJBAqSLDzEevYr9Ap', 'Ava - youthful and expressive German female voice'),
    ('CnVVMwhKmKZ6hKBAkL6Y', 'Giulia - sweet and soothing'),
    ('DLMxnwJE0a28JQLTMJPJ', 'Andy M - Italian male warm expressive'),
    ('F7eI6slaNFiCSAjYVX5H', 'Dante - Italian, 30 years old'),
    ('F9w7aaEjfT09qV89OdY8', 'Voce Minatore Audiolibro'),
    ('IxprfqLvLirqXn7FdoLy', 'Ronny Pro'),
    ('K1tUDof5PBLHFWSha7Rk', 'Giacomo Andreoli'),
    ('MP7UPhn7eVWqCGJGIh6Q', 'Aaron Patrick - Fun-Upbeat'),
    ('NHKPYzJJpg27vbywLSzX', 'Rossana'),
    ('PBm6YPbx7WbrxFTZwj3E', 'Gabriel - French high quality'),
    ('PSp7S6ST9fDNXDwEzX0m', 'Alessandro'),
    ('QRtC9QO1TMWv4NedDNQo', 'Christopher'),
    ('SKiSiJy90hYzWch2Gohz', 'Christopher - scientific mind'),
    ('SpoXt7BywHwFLisCTpQ3', 'GianP - Social Media & Ads'),
    ('WS5NDpCHnVmKWdD3oolF', 'Hannah - assertive & refined'),
    ('YNOujSUmHtgN6anjqXPf', 'Victor Power - Ebooks'),
    ('cyD08lEy76q03ER1jZ7y', 'ScheilaSMTy'),
    ('g1X9mrbeBlMAWtcs2Dfp', 'Chris Basetta - Profonda'),
    ('kmIocz8ptnzGYxNhfW6f', 'Luca'),
    ('lcweSB9PJMspXEFIqkPb', 'Francesco'),
    ('lnUnPeUhSI5EcqtFBux7', 'Bill - Health Nutrition Videos'),
    ('raMcNf2S8wCmuaBcyI6E', 'Tyler Kurk'),
    ('t3hJ92dgZhDVtsff084B', 'Chris Basetta - Social Media'),
    ('tXgbXPnsMpKXkuTgvE3h', 'Elena - Stories and Narrations'),
    ('uFIXVu9mmnDZ7dTKCBTX', 'Justin Time - eLearning Narration'),
    ('vTGV06pygfwa2WhLDZFp', 'French Darling - For Kids Stories and Audiobooks'),
    ('xKlYVm5xfEkeK36yeDDj', 'Emanuel'),
    ('yfg5cjOrqg6KVleh2la0', 'Adam'),
]


class ElevenlabsTextToSpeechSerializer(serializers.Serializer):
    send = serializers.CharField()
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES)
    id_voice = serializers.ChoiceField(choices=VOICE_CHOICES)
    stability = serializers.FloatField(
        required=False, min_value=0.0, max_value=1.0, default=0.5)
    similarity_boost = serializers.FloatField(
        required=False, min_value=0.0, max_value=1.0, default=0.0)
    style = serializers.FloatField(
        required=False, min_value=0.0, max_value=1.0, default=0.6)
    use_speaker_boost = serializers.BooleanField(required=False, default=False)

    def validate_language(self, value):
        if value not in ['en', 'it', 'fr', 'de', 'pt', 'el', 'es']:
            raise serializers.ValidationError(
                'Invalid language. Allowed language are "el"[Greek], "en"[English], "es"[Spanish],"it"[Italian], "fr"[French], "de"[German] and "pt"[Portuguese].'
            )
        return value
