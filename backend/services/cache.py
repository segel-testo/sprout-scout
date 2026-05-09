import hashlib
import json
import os
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_TTL = 60 * 60 * 24 * 7  # 1 week in seconds

S3_BUCKET = os.environ.get("CACHE_S3_BUCKET")
S3_ACCESS_KEY = os.environ.get("CACHE_S3_ACCESS_KEY")
S3_SECRET_KEY = os.environ.get("CACHE_S3_SECRET_KEY")
S3_ENDPOINT = os.environ.get("CACHE_S3_ENDPOINT", "https://s3.fr-par.scw.cloud")
S3_REGION = os.environ.get("CACHE_S3_REGION", "fr-par")

USE_S3 = bool(S3_BUCKET and S3_ACCESS_KEY and S3_SECRET_KEY)

if USE_S3:
    import boto3
    from botocore.exceptions import ClientError

    _s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        region_name=S3_REGION,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )
else:
    CACHE_DIR.mkdir(exist_ok=True)


def _digest(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def get_cached(key: str):
    name = f"{_digest(key)}.json"
    if USE_S3:
        try:
            obj = _s3.get_object(Bucket=S3_BUCKET, Key=name)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            raise
        data = json.loads(obj["Body"].read())
    else:
        path = CACHE_DIR / name
        if not path.exists():
            return None
        data = json.loads(path.read_text())

    if time.time() - data["timestamp"] > CACHE_TTL:
        if USE_S3:
            _s3.delete_object(Bucket=S3_BUCKET, Key=name)
        else:
            (CACHE_DIR / name).unlink()
        return None
    return data["payload"]


def set_cached(key: str, payload):
    name = f"{_digest(key)}.json"
    body = json.dumps({"timestamp": time.time(), "payload": payload})
    if USE_S3:
        _s3.put_object(Bucket=S3_BUCKET, Key=name, Body=body.encode("utf-8"))
    else:
        (CACHE_DIR / name).write_text(body)


def get_namespaced(namespace: str, key: str):
    return get_cached(f"{namespace}__{key}")


def set_namespaced(namespace: str, key: str, payload):
    set_cached(f"{namespace}__{key}", payload)
