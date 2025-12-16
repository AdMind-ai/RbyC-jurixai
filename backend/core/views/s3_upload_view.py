from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
import boto3
import uuid
import jwt
from datetime import datetime, timedelta


class S3UploadView(APIView):
    """Simple endpoint to upload a single file to S3.

    Expects multipart/form-data with a `file` field. Optional `key` field
    to set the object key/path in the bucket. Returns the object key and
    a public URL (if bucket is public) or the key for further usage.
    """

    # Prevent DRF authenticators (e.g. SimpleJWT) from trying to validate
    # the Authorization header before our custom check. Use AllowAny so
    # the view can perform its own validation.
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # Validate JWT from Authorization header
        payload, err = self._validate_jwt(request)
        if err:
            return err
        # Accept multiple files: client can POST several fields named 'file'
        files = request.FILES.getlist('file')
        if not files:
            return Response({'detail': 'No file provided (field "file" required).'}, status=status.HTTP_400_BAD_REQUEST)

        # Optional: client can pass comma-separated keys in `keys` matching number of files
        keys_param = request.data.get('keys')
        keys = None
        if keys_param:
            # simple comma-separated parsing
            keys = [k.strip() for k in keys_param.split(',') if k.strip()]
            if len(keys) != len(files):
                return Response({'detail': 'Number of keys does not match number of files.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', None),
        )

        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        if not bucket:
            return Response({'detail': 'S3 bucket not configured (AWS_STORAGE_BUCKET_NAME).'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        results = []
        for idx, f in enumerate(files):
            file_key = keys[idx] if keys else f.name 
            try:
                s3_client.upload_fileobj(
                    f,
                    bucket,
                    file_key,
                    ExtraArgs={
                        'ContentType': f.content_type or 'application/octet-stream',
                    }
                )
                region = getattr(settings, 'AWS_S3_REGION_NAME', None)
                if region:
                    url = f"https://{bucket}.s3.{region}.amazonaws.com/{file_key}"
                else:
                    url = f"https://{bucket}.s3.amazonaws.com/{file_key}"

                results.append({'file': f.name, 'key': file_key, 'url': url, 'status': 'uploaded'})
            except Exception as e:
                results.append({'file': f.name, 'key': file_key, 'status': 'error', 'error': str(e)})

        # If all succeeded return 201, otherwise 207 Multi-Status with per-file details
        all_ok = all(r.get('status') == 'uploaded' for r in results)
        return Response({'results': results}, status=(status.HTTP_201_CREATED if all_ok else status.HTTP_207_MULTI_STATUS))
    
    def _validate_jwt(self, request):
        # Only accept token from the Authorization header (HTTP_AUTHORIZATION).
        auth = request.META.get('HTTP_AUTHORIZATION')
        if not auth:
            return None, Response({'detail': 'Authorization header missing.'}, status=status.HTTP_401_UNAUTHORIZED)

        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None, Response({'detail': 'Invalid authorization header.'}, status=status.HTTP_401_UNAUTHORIZED)

        token = parts[1]
        secret = getattr(settings, 'S3_UPLOAD_JWT_SECRET', None) or settings.SECRET_KEY
        try:
            payload = jwt.decode(token, secret, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None, Response({'detail': 'Token expired.'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return None, Response({'detail': 'Invalid token.', 'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        # Check scope
        if payload.get('scope') != 's3:upload':
            return None, Response({'detail': 'Token missing required scope.'}, status=status.HTTP_403_FORBIDDEN)

        return payload, None

class S3TokenView(APIView):
    """Endpoint to obtain a short-lived JWT for S3 uploads.

    Clients must provide the configured `S3_UPLOAD_API_KEY` ONLY via the
    `Authorization` header using the `ApiKey` scheme:

        Authorization: ApiKey <API_KEY>

    This view returns a JWT with scope 's3:upload' and expiration controlled
    by `S3_UPLOAD_JWT_EXP` (seconds).
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # Require API key only via Authorization: ApiKey <key>
        auth = request.META.get('HTTP_AUTHORIZATION') or request.headers.get('Authorization')
        api_key = None
        if auth:
            parts = auth.split()
            if len(parts) == 2 and parts[0].lower() in ('apikey', 'api-key', 'api_key'):
                api_key = parts[1]

        configured = getattr(settings, 'S3_UPLOAD_API_KEY', None)
        if not configured:
            return Response({'detail': 'Server not configured to issue upload tokens.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not api_key:
            return Response({'detail': 'Missing API key. Provide header: Authorization: ApiKey <API_KEY>'}, status=status.HTTP_401_UNAUTHORIZED)

        if api_key != configured:
            return Response({'detail': 'Invalid API key.'}, status=status.HTTP_401_UNAUTHORIZED)

        secret = getattr(settings, 'S3_UPLOAD_JWT_SECRET', None) or settings.SECRET_KEY
        exp_seconds = getattr(settings, 'S3_UPLOAD_JWT_EXP', 3600)
        now = datetime.utcnow()
        payload = {
            'scope': 's3:upload',
            'iat': now,
            'exp': now + timedelta(seconds=exp_seconds),
        }

        token = jwt.encode(payload, secret, algorithm='HS256')
        return Response({'token': token, 'expires_in': exp_seconds}, status=status.HTTP_200_OK)
