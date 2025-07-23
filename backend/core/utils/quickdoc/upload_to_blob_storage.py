from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timedelta
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from django.conf import settings


def upload_to_blob_storage(file_data, blob_name):
    # Create the BlobServiceClient object
    blob_service_client = BlobServiceClient.from_connection_string(
        settings.AZURE_CONNECTION_STRING)

    try:
        container_client = blob_service_client.create_container(
            name=settings.AZURE_CONTAINER_NAME)
        container_client.upload_blob(
            data=file_data, blob_type="BlockBlob", overwrite=settings.AZURE_OVERWRITE_FILES)
    except ResourceExistsError:
        container_client = blob_service_client.get_blob_client(
            container=settings.AZURE_CONTAINER_NAME, blob=blob_name)
        container_client.upload_blob(
            data=file_data, blob_type="BlockBlob", overwrite=settings.AZURE_OVERWRITE_FILES)

    sas_token = generate_sas_token(blob_name)

    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{settings.AZURE_CONTAINER_NAME}/{blob_name}?{sas_token}"

    return blob_url


def generate_sas_token(blob_name):
    start_time = datetime.utcnow()  # Hora atual
    expiry_time = start_time + timedelta(hours=1)  # Espiração em 1hr

    # Gera um SAS Token para acesso seguro ao arquivo no Blob Storage
    sas_token = generate_blob_sas(
        account_name=settings.AZURE_ACCOUNT_NAME,
        container_name=settings.AZURE_CONTAINER_NAME,
        blob_name=blob_name,
        account_key=settings.AZURE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        start=start_time,  # Define início válido
        expiry=expiry_time
    )
    return sas_token
