"""
Modul penanganan dan normalisasi metadata orientasi EXIF citra.
"""

from typing import Optional
from PIL import Image, ImageOps
import logging

logger = logging.getLogger(__name__)

EXIF_ORIENTATION_TAG = 0x0112  # Tag 274 dalam EXIF standar


def get_exif_orientation(image: Image.Image) -> Optional[int]:
    """
    Mengambil nilai numerik tag orientasi EXIF (1 hingga 8), jika ada.
    """
    try:
        exif = image.getexif()
        if exif:
            return exif.get(EXIF_ORIENTATION_TAG)
    except Exception as exc:
        logger.debug("Tidak dapat membaca data EXIF: %s", exc)
    return None


def normalize_exif_orientation(image: Image.Image) -> Image.Image:
    """
    Menormalkan orientasi fisik citra berdasarkan tag EXIF Orientation.
    Jika citra memiliki tag orientasi (portrait/landscape yang tersimpan miring),
    citra akan ditranspose/dirotasi ke orientasi tegak yang benar dan tag direset.
    """
    try:
        transposed = ImageOps.exif_transpose(image)
        if transposed is not None:
            return transposed
    except Exception as exc:
        logger.warning("Gagal memproses EXIF orientation transposition: %s", exc)
    return image
