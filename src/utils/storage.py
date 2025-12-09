import base64
import os
import uuid
from typing import Optional

import boto3
from botocore.config import Config

from .crypto import encrypt_str


def _s3_configured() -> bool:
    required = [
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_BUCKET",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "APP_ENCRYPTION_KEY",
    ]
    return all(os.environ.get(k) for k in required)


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        region_name=os.environ["S3_REGION"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )


def upload_encrypted_pdf(user_id: Optional[int], filename: str, data: bytes) -> Optional[str]:
    """
    Encrypt and upload PDF bytes to S3-compatible storage. Returns object key or None on failure/disabled.
    """
    if not _s3_configured():
        return None

    try:
        # Encrypt content (base64 for binary)
        b64_payload = base64.b64encode(data).decode()
        encrypted_payload = encrypt_str(b64_payload)
        object_key = f"{os.environ.get('S3_PREFIX','uploads')}/user_{user_id or 'anon'}/{uuid.uuid4()}_{filename}"

        client = _s3_client()
        put_kwargs = {
            "Bucket": os.environ["S3_BUCKET"],
            "Key": object_key,
            "Body": encrypted_payload.encode(),
            "ContentType": "application/octet-stream",
        }
        if os.environ.get("S3_SSE", "").upper() == "AES256":
            put_kwargs["ServerSideEncryption"] = "AES256"

        client.put_object(**put_kwargs)
        return object_key
    except Exception:
        return None
