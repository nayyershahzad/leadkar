"""S3-compatible object storage wrapper (MinIO now; Hetzner OS / R2 later).

Uploads use the internal endpoint (S3_ENDPOINT); presigned download URLs are
generated against the public endpoint (S3_PUBLIC_ENDPOINT) so customer browsers
can reach them. Path-style addressing is used (MinIO + a single TLS host).
"""

from __future__ import annotations

import boto3
from botocore.client import Config

from app.config import settings

_CFG = Config(signature_version="s3v4", s3={"addressing_style": "path"})


def _client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=_CFG,
    )


class S3Storage:
    def __init__(self) -> None:
        self._client = _client(settings.S3_ENDPOINT)
        # Presign against the public host so emailed links resolve for customers.
        public = settings.S3_PUBLIC_ENDPOINT or settings.S3_ENDPOINT
        self._public = _client(public)

    def ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist (idempotent)."""
        import botocore.exceptions

        try:
            self._client.head_bucket(Bucket=settings.S3_BUCKET)
        except botocore.exceptions.ClientError:
            self._client.create_bucket(Bucket=settings.S3_BUCKET)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=settings.S3_BUCKET, Key=key, Body=data, ContentType=content_type
        )

    def presign_get(self, key: str, expires_seconds: int | None = None) -> str:
        ttl = expires_seconds or settings.S3_PRESIGNED_URL_TTL_HOURS * 3600
        return self._public.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=ttl,
        )

    def copy(self, src_key: str, dst_key: str) -> None:
        self._client.copy_object(
            Bucket=settings.S3_BUCKET,
            CopySource={"Bucket": settings.S3_BUCKET, "Key": src_key},
            Key=dst_key,
        )
