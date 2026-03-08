from __future__ import annotations

import boto3
from botocore.client import BaseClient


class ObjectStorage:
    def __init__(
        self,
        *,
        access_key: str | None,
        secret_key: str | None,
        bucket_name: str | None,
        endpoint_url: str,
        region_name: str,
    ) -> None:
        self.bucket_name = bucket_name
        self._client: BaseClient | None = None
        if access_key and secret_key and bucket_name:
            self._client = boto3.client(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint_url,
                region_name=region_name,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None and self.bucket_name is not None

    def presigned_get_url(self, key: str | None, expires_in: int = 3600) -> str | None:
        if not self.enabled or key is None or self.bucket_name is None or self._client is None:
            return None
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
