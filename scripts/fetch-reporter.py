#!/usr/bin/env python3
"""Fetch the immutable official collector for an offline compatibility test."""
import hashlib
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
pin = dict(line.split("=", 1) for line in (root / "vendor/client.pin").read_text().splitlines() if "=" in line)
url = f"https://raw.githubusercontent.com/plow-pbc/agent-index-client/{pin['sha']}/{pin['path']}"
data = urllib.request.urlopen(url, timeout=30).read()
if hashlib.sha256(data).hexdigest() != pin["sha256"]:
    raise SystemExit("Collector checksum mismatch")
(root / "work").mkdir(exist_ok=True)
(root / "work/agent_index_client.py").write_bytes(data)
print("Official collector fetched and checksum verified.")
