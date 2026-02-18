"""Azure Blob Storage service for file management."""

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple, BinaryIO
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceNotFoundError

from ..config import settings

logger = logging.getLogger(__name__)


class BlobStorageService:
    """Service for Azure Blob Storage operations."""

    def __init__(self):
        """Initialize blob storage client."""
        self._client: Optional[BlobServiceClient] = None

    def _create_client(self) -> BlobServiceClient:
        """Create a fresh BlobServiceClient."""
        if settings.azure_storage_connection_string:
            return BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
        elif (
            settings.azure_storage_account_name
            and settings.azure_storage_account_key
        ):
            account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
            return BlobServiceClient(
                account_url=account_url,
                credential=settings.azure_storage_account_key,
            )
        else:
            raise ValueError("Azure Blob Storage credentials not configured")

    @property
    def client(self) -> BlobServiceClient:
        """Get or create blob service client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _reset_client(self) -> None:
        """Drop the current client so the next access creates a fresh one."""
        logger.warning("Resetting Azure Blob Storage client due to connection failure")
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass
        self._client = None

    def _ensure_container_exists(self, container_name: str) -> None:
        """Ensure container exists, create if not."""
        try:
            container_client = self.client.get_container_client(container_name)
            if not container_client.exists():
                container_client.create_container()
        except Exception:
            # Container might already exist or we don't have permissions
            pass

    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension."""
        extension = filename.lower().split(".")[-1] if "." in filename else ""
        content_types = {
            "pdf": "application/pdf",
            "html": "text/html",
            "htm": "text/html",
            "txt": "text/plain",
            "json": "application/json",
            "xml": "application/xml",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return content_types.get(extension, "application/octet-stream")

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum."""
        return hashlib.sha256(data).hexdigest()

    def upload_file(
        self,
        container: str,
        file_data: bytes,
        filename: str,
        folder: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Tuple[str, str, str, int]:
        """
        Upload a file to Azure Blob Storage.

        Args:
            container: Container name (raw-documents, processed-documents, uploads)
            file_data: File content as bytes
            filename: Original filename
            folder: Optional folder path within container
            metadata: Optional metadata to attach to blob

        Returns:
            Tuple of (blob_path, blob_url, checksum, file_size)
        """
        self._ensure_container_exists(container)

        # Generate unique blob name
        unique_id = str(uuid.uuid4())
        extension = filename.split(".")[-1] if "." in filename else ""
        blob_name = f"{unique_id}.{extension}" if extension else unique_id

        # Add folder prefix if provided
        if folder:
            blob_path = f"{folder.strip('/')}/{blob_name}"
        else:
            blob_path = blob_name

        # Calculate checksum
        checksum = self._calculate_checksum(file_data)
        file_size = len(file_data)

        content_settings = ContentSettings(
            content_type=self._get_content_type(filename)
        )

        blob_metadata = {
            "original_filename": filename,
            "checksum": checksum,
            "uploaded_at": datetime.utcnow().isoformat(),
        }
        if metadata:
            blob_metadata.update(metadata)

        # Retry once with a fresh client on connection/SSL failures
        for attempt in range(2):
            try:
                blob_client = self.client.get_blob_client(
                    container=container, blob=blob_path
                )
                blob_client.upload_blob(
                    file_data,
                    content_settings=content_settings,
                    metadata=blob_metadata,
                    overwrite=True,
                )
                blob_url = blob_client.url
                return blob_path, blob_url, checksum, file_size
            except (ConnectionError, OSError, TimeoutError) as e:
                if attempt == 0:
                    logger.warning(f"Blob upload failed (attempt 1), reconnecting: {e}")
                    self._reset_client()
                else:
                    raise

    def upload_stream(
        self,
        container: str,
        file_stream: BinaryIO,
        filename: str,
        folder: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Tuple[str, str, str, int]:
        """
        Upload a file stream to Azure Blob Storage.

        Args:
            container: Container name
            file_stream: File-like object
            filename: Original filename
            folder: Optional folder path
            metadata: Optional metadata

        Returns:
            Tuple of (blob_path, blob_url, checksum, file_size)
        """
        # Read stream into memory for checksum calculation
        file_data = file_stream.read()
        return self.upload_file(container, file_data, filename, folder, metadata)

    def download_file(self, container: str, blob_path: str) -> Optional[bytes]:
        """
        Download a file from Azure Blob Storage.

        Args:
            container: Container name
            blob_path: Path to blob within container

        Returns:
            File content as bytes, or None if not found
        """
        try:
            blob_client = self.client.get_blob_client(
                container=container, blob=blob_path
            )
            download_stream = blob_client.download_blob()
            return download_stream.readall()
        except ResourceNotFoundError:
            return None
        except Exception:
            return None

    def delete_file(self, container: str, blob_path: str) -> bool:
        """
        Delete a file from Azure Blob Storage.

        Args:
            container: Container name
            blob_path: Path to blob within container

        Returns:
            True if deleted, False if not found or error
        """
        try:
            blob_client = self.client.get_blob_client(
                container=container, blob=blob_path
            )
            blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False
        except Exception:
            return False

    def file_exists(self, container: str, blob_path: str) -> bool:
        """Check if a file exists in blob storage."""
        try:
            blob_client = self.client.get_blob_client(
                container=container, blob=blob_path
            )
            return blob_client.exists()
        except Exception:
            return False

    def get_blob_url(self, container: str, blob_path: str) -> str:
        """Get the URL for a blob."""
        blob_client = self.client.get_blob_client(container=container, blob=blob_path)
        return blob_client.url

    def list_blobs(self, container: str, prefix: Optional[str] = None) -> list:
        """
        List blobs in a container.

        Args:
            container: Container name
            prefix: Optional path prefix to filter

        Returns:
            List of blob names
        """
        try:
            container_client = self.client.get_container_client(container)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception:
            return []

    def is_configured(self) -> bool:
        """Check if blob storage is configured."""
        return bool(
            settings.azure_storage_connection_string
            or (
                settings.azure_storage_account_name
                and settings.azure_storage_account_key
            )
        )


# Singleton instance
_blob_service: Optional[BlobStorageService] = None


def get_blob_storage_service() -> BlobStorageService:
    """Get or create blob storage service singleton."""
    global _blob_service
    if _blob_service is None:
        _blob_service = BlobStorageService()
    return _blob_service
