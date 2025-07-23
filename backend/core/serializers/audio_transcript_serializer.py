import os

from rest_framework import serializers


class AudioTranscriptSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        _, extension = os.path.splitext(value.name)
        ACCEPTED_EXTENSIONS = ['.mp4', '.mp3', '.wav', '.mpeg', '.webm']
        if extension not in ACCEPTED_EXTENSIONS:
            accepted_str = ', '.join(ACCEPTED_EXTENSIONS)
            raise serializers.ValidationError(
                f'invalid extension. File formats must be: {accepted_str}. File is {extension} type'
            )
        return value
