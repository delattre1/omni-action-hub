"""Preserve the original evidence; optimize only the Gemini representation."""
import io

from PIL import Image, ImageOps

from .models import Problem


def optimize_for_vision(data, budget=999_999):
    with Image.open(io.BytesIO(data)) as original:
        if original.width * original.height > 25_000_000:
            raise Problem("vision_size", "Envie uma captura menor.")
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
        lossless = io.BytesIO()
        image.save(lossless, "PNG", optimize=True)
        if len(lossless.getvalue()) <= budget:
            return lossless.getvalue(), "image/png"
        # Keep sharp color edges: no chroma subsampling. Avoid very low quality.
        for side in (2048, 1792, 1536, 1280, 1024):
            candidate = image.copy()
            candidate.thumbnail((side, side), Image.Resampling.LANCZOS)
            for quality in (90, 82, 75):
                out = io.BytesIO()
                candidate.save(out, "JPEG", quality=quality, subsampling=0)
                if len(out.getvalue()) <= budget:
                    return out.getvalue(), "image/jpeg"
    raise Problem("vision_size", "Não consegui reduzir a imagem preservando qualidade suficiente. Envie um recorte da área com erro.")
