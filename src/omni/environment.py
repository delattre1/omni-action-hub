"""Load the environment published by Plow bootstrap, without execlineb."""
import os
import stat
from pathlib import Path

PLOW_KEYS = ("PLOW_API_BASE", "PLOW_AGENT_TOKEN", "PLOW_HOME_CHANNEL", "PLOW_MCP_URL")


def load_runtime_environment(root=Path("/run/s6/container_environment")):
    """docker exec starts with the original Docker env, not s6's updates.

    Only bootstrap-owned, non-world/group-writable regular files are trusted.
    Existing application settings and API keys are never overwritten here.
    """
    for name in PLOW_KEYS:
        path = root / name
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                continue
            value = path.read_text().rstrip("\n\x00")
            if value:
                os.environ[name] = value
        except (FileNotFoundError, PermissionError):
            continue
