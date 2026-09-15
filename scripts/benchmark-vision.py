"""Reproducible, offline payload benchmark; does not measure OCR quality."""
import io
import json
import random
import time

from PIL import Image

from omni.vision import optimize_for_vision


def main():
    source = io.BytesIO()
    pixels = random.Random(20260914).randbytes(1920 * 1080 * 3)
    Image.frombytes("RGB", (1920, 1080), pixels).save(source, "PNG")
    started = time.perf_counter()
    data, mime = optimize_for_vision(source.getvalue())
    elapsed = (time.perf_counter() - started) * 1000
    with Image.open(io.BytesIO(data)) as image:
        print(json.dumps({"source_bytes": len(source.getvalue()), "vision_bytes": len(data),
                          "mime": mime, "width": image.width, "height": image.height,
                          "elapsed_ms": round(elapsed, 2), "ocr_quality_tested": False}, indent=2))


if __name__ == "__main__":
    main()
