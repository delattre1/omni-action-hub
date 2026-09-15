#!/bin/sh
# Use a Python environment with this project and its test extra installed.
set -eu
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" -m pytest -q -s tests/test_image_buffer.py tests/test_gateway.py tests/test_clients.py tests/test_media.py
