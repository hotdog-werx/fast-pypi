import os
import re
from typing import Annotated, Literal, cast

from pydantic import BaseModel, Field, SecretStr

_DESTINATION_PATH_PATTERN = re.compile(r'^(https?://[^/]+(?::\d+)?)/([^/]+)/(.+/)$')


class AzureBlobConfig(BaseModel):
    """Configuration for the azure blob backend."""

    # Includes the account URL, container name, and base path in the format
    # <account url>/<container_name>/<base_path>
    # E.g., https://<account_name>.blob.core.windows.net/<container_name>/<base_path>
    destination_path: Annotated[
        str,
        Field(pattern=_DESTINATION_PATH_PATTERN),
    ]
    # Optional connection string, otherwise uses DefaultAzureCredential
    connection_string: SecretStr | None = None
    connection_method: Literal['default', 'managed_identity'] = 'default'

    @classmethod
    def from_env(cls) -> 'AzureBlobConfig':
        """Create a AzureBlobEnvConfig instance from environment variables."""
        return AzureBlobConfig.model_validate(
            {
                'destination_path': os.getenv('FAST_PYPI_AZURE_BLOB_DESTINATION_PATH'),
                'connection_string': os.getenv('FAST_PYPI_AZURE_BLOB_CONNECTION_STRING'),
                'connection_method': os.getenv('FAST_PYPI_AZURE_BLOB_CONNECTION_METHOD', 'default'),
            }
        )

    def parse_destination_path(self) -> tuple[str, str, str]:
        """Parse the destination path into account URL, container name, and base path."""
        # Note we can cast here - the regex validation pattern in the class
        # definition ensures that the destination_path matches the expected
        # format.
        match = cast(
            're.Match[str]',
            _DESTINATION_PATH_PATTERN.match(self.destination_path),
        )
        account_url, container_name, base_path = match.groups()
        return account_url, container_name, base_path
