"""Hetzner Object Storage (S3 API) wrapper (CLAUDE.md §4)."""

from __future__ import annotations

import boto3
from botocore.client import Config

from app.config import settings


class S3Storage:
    """Thin sync boto3 wrapper. Used from Celery tasks (which are sync)."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=settings.S3_BUCKET, Key=key, Body=data, ContentType=content_type
        )

    def presign_get(self, key: str, expires_seconds: int | None = None) -> str:
        ttl = expires_seconds or settings.S3_PRESIGNED_URL_TTL_HOURS * 3600
        return self._client.generate_presigned_url(
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
