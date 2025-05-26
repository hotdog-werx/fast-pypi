from collections.abc import Sequence
from logging import getLogger

from typing_extensions import override

from fast_pypi.backend import AbstractBackendInterface

from .azure_blob_utils import azure_blob_container_client
from .env import AzureBlobConfig

logger = getLogger(__name__)


class AzureBlobBackend(AbstractBackendInterface):
    """Interface for the azure blob backend."""

    config: AzureBlobConfig

    def __init__(self, config: AzureBlobConfig, *, allow_overwrite: bool = False) -> None:
        self.config = config
        super().__init__(allow_overwrite=allow_overwrite)

    @override
    async def list_projects(self) -> Sequence[str]:
        """List all projects in the local file system.

        Returns:
            A sequence of project names.
        """
        async with azure_blob_container_client(config=self.config) as (container_client, base_path):
            blob_props = [
                blob_prop async for blob_prop in container_client.walk_blobs(name_starts_with=base_path, delimiter='/')
            ]

        return [blob_prop.name.split('/')[1] for blob_prop in blob_props if '/' in blob_prop.name]
