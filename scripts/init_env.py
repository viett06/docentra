"""Create local-only configuration without overwriting an existing developer's settings."""

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / ".env"
content = path.read_text() if path.exists() else ""
defaults = {
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5433",
    "POSTGRES_DB": "docentra",
    "POSTGRES_USER": "docentra",
    "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
    "S3_ENDPOINT": "http://127.0.0.1:9002",
    "S3_ACCESS_KEY": "docentra-local-admin",
    "S3_SECRET_KEY": secrets.token_urlsafe(32),
    "S3_BUCKET": "docentra-private",
    "DEMO_MODE": "true",
    "DEMO_PASSWORD": "DocentraDemo!2026",
    "COOKIE_SECURE": "false",
}
present = {
    line.split("=", 1)[0].strip() for line in content.splitlines() if "=" in line and not line.lstrip().startswith("#")
}
if content and not content.endswith("\n"):
    content += "\n"
for key, value in defaults.items():
    if key not in present:
        content += f"{key}={value}\n"
path.write_text(content)
path.chmod(0o600)
print("Local .env is ready. Existing values were preserved; credentials were not printed.")
