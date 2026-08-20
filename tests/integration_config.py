from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_REPOSITORY_ROOT / ".env")


def env_value(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value not in (None, ""):
            return value
    return default


def env_required(*names: str) -> str:
    value = env_value(*names)
    if value is None:
        raise RuntimeError(f"Missing required integration setting: {names[0]}")
    return value


def env_flag(*names: str) -> bool:
    value = env_value(*names, default="")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def windows_auth_enabled() -> bool:
    return env_flag("SQLSERVER_WINDOWS_AUTH")
