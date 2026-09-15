#!/usr/bin/env python3
"""Download the source actually pinned by the chosen base image, for contract tests."""
import hashlib
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sha = "baa1261174469744b9d915f062f7bdb2e304f9a5"
url = f"https://raw.githubusercontent.com/plow-pbc/hermes-plugin-plow/{sha}/plow-chat-platform/__init__.py"
data = urllib.request.urlopen(url, timeout=30).read()
if hashlib.sha256(data).hexdigest() != "923353d62f56b9f9f9288c8f322e551c328234d882d9f17a9c750f1c248f7f0a":
    raise SystemExit("Transport checksum mismatch")
(root / "work").mkdir(exist_ok=True)
(root / "work/pinned-transport.py").write_bytes(data)
print("Pinned Plow transport source fetched and checksum verified.")
