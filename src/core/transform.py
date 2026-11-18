"""
Modul transformasi citra: smart resize, center-crop, dan penjagaan rasio aspek.
"""

from typing import Tuple
from PIL import Image


def resize_and_center_crop(
    image: Image.Image,
    target_size: Tuple[int, int],
    resample: Image.Resampling = Image.Resampling.LANCZOS
) -> Image.Image:
    """
    Mengubah ukuran citra dengan mempertahankan rasio aspek asli (mode Cover / Aspect Fill),
    kemudian melakukan pemotongan simetris dari titik tengah (center crop) agar dimensi
    citra tepat sesuai dengan target_size (width, height).

    Mendukung foto portrait, landscape, maupun persegi tanpa mengalami distorsi bentuk.

    :param image: Citra sumber (Pillow Image).
    :param target_size: Ukuran target berupa tuple (target_width, target_height).
    :param resample: Filter resampling Pillow (default: LANCZOS untuk ketajaman optimal).
    :return: Citra baru hasil crop & resize dengan ukuran presisi target_size.
    """
    target_w, target_h = target_size

    if target_w <= 0 or target_h <= 0:
        raise ValueError(f"Ukuran target harus bernilai positif (> 0), diterima: {target_size}")

    img_w, img_h = image.size
    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"Dimensi citra tidak valid: {image.size}")

    # Hitung rasio penskalaan agar menutup penuh target_size (Aspect Fill)
    scale = max(target_w / img_w, target_h / img_h)
    new_w = max(1, int(round(img_w * scale)))
    new_h = max(1, int(round(img_h * scale)))

    # Penskalaan proporsional
    resized = image.resize((new_w, new_h), resample=resample)

    # Pemotongan simetris di bagian tengah
    left = max(0, (new_w - target_w) // 2)
    top = max(0, (new_h - target_h) // 2)
    right = left + target_w
    bottom = top + target_h

    # Penanganan pembulatan batas jika ada selisih piksel minor
    if right > new_w:
        right = new_w
        left = max(0, right - target_w)
    if bottom > new_h:
        bottom = new_h
        top = max(0, bottom - target_h)

    cropped = resized.crop((left, top, right, bottom))

    # Pastikan ukuran persis sesuai target
    if cropped.size != (target_w, target_h):
        cropped = cropped.resize((target_w, target_h), resample=resample)

    return cropped
