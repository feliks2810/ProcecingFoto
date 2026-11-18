"""
Modul pendeteksian otomatis area lubang transparan (alpha < 128) pada frame PNG.
"""

from typing import Optional
from PIL import Image

from src.config.models import SlotCoordinates


def detect_transparent_hole(frame: Image.Image, alpha_threshold: int = 128) -> Optional[SlotCoordinates]:
    """
    Menganalisis saluran alpha dari frame PNG untuk menemukan batas koordinat
    persegi (bounding box) area transparan yang disediakan untuk foto.

    :param frame: Citra frame PNG (harus memiliki saluran alpha atau mode RGBA).
    :param alpha_threshold: Nilai ambang alpha untuk dianggap transparan (default: < 128).
    :return: SlotCoordinates jika ditemukan area transparan, atau None jika frame solid penuh.
    """
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")

    alpha_channel = frame.split()[3]

    # Inversi: area transparan (< alpha_threshold) diberi nilai 255 (putih),
    # area ornamen bingkai (>= alpha_threshold) diberi nilai 0 (hitam).
    inv_mask = Image.eval(alpha_channel, lambda a: 255 if a < alpha_threshold else 0)

    # Dapatkan bounding box dari piksel non-nol (area transparan)
    bbox = inv_mask.getbbox()
    if not bbox:
        return None

    x1, y1, x2, y2 = bbox
    width = max(10, x2 - x1)
    height = max(10, y2 - y1)

    # Validasi tidak melampaui kanvas frame
    fw, fh = frame.size
    x = max(0, min(fw - 10, x1))
    y = max(0, min(fh - 10, y1))
    w = max(10, min(fw - x, width))
    h = max(10, min(fh - y, height))

    return SlotCoordinates(x=x, y=y, width=w, height=h)
