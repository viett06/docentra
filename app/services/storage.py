import warnings
from functools import lru_cache
from io import BytesIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import AppError


@lru_cache
def client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 2},
            connect_timeout=3,
            read_timeout=15,
        ),
    )


def ensure_bucket():
    bucket = get_settings().S3_BUCKET
    try:
        client().head_bucket(Bucket=bucket)
    except ClientError as exc:
        if str(exc.response["Error"]["Code"]) not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        client().create_bucket(Bucket=bucket)


def put_object(key: str, data: bytes, mime: str):
    # Callers allocate an unguessable new page/job ID; existing originals are never overwritten.
    client().put_object(Bucket=get_settings().S3_BUCKET, Key=key, Body=data, ContentType=mime)


def read_object(key: str) -> bytes:
    response = client().get_object(Bucket=get_settings().S3_BUCKET, Key=key)
    try:
        return response["Body"].read()
    finally:
        response["Body"].close()


def validate_image(data: bytes):
    if not data or len(data) > get_settings().MAX_UPLOAD_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", "Ảnh trống hoặc lớn hơn giới hạn 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(image.format)
                if not mime or image.width * image.height > 24_000_000 or min(image.size) < 100:
                    raise ValueError("unsupported image")
                width, height = image.size
                image.verify()
        return mime, width, height
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AppError(422, "INVALID_IMAGE", "Chỉ nhận ảnh JPEG, PNG hoặc WebP hợp lệ, tối đa 24 megapixel.") from None
