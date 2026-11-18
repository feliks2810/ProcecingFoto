"""
Modul penyimpanan citra aman (safe atomic write & non-destructive collision prevention).
"""

import os
import time
from pathlib import Path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def get_unique_filepath(target_path: Path) -> Path:
    """
    Menghasilkan path file unik jika target_path sudah ada di direktori tujuan,
    dengan menambahkan sufiks counter (_1, _2, dst.) sebelum ekstensi.
    Mencegah penimpaan file output yang sudah ada.
    """
    if not target_path.exists():
        return target_path

    parent = target_path.parent
    stem = target_path.stem
    suffix = target_path.suffix
    counter = 1

    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def save_image_safely(
    image: Image.Image,
    output_path: Path,
    export_format: str = "PNG",
    quality: int = 95,
    allow_overwrite: bool = False
) -> Path:
    """
    Menyimpan citra ke disk secara non-destructive dan atomic:
    1. Menyelesaikan konflik nama (menghindari penimpaan jika allow_overwrite=False).
    2. Menulis data terlebih dahulu ke file temporer (.tmp_...) di direktori yang sama.
    3. Mengganti nama file temporer ke nama target secara atomic (os.replace).
    4. Menjamin file sumber tidak pernah disentuh atau dimodifikasi.

    :param image: Citra Pillow yang akan disimpan.
    :param output_path: Jalur tujuan file yang diinginkan.
    :param export_format: Format file ('PNG' atau 'JPEG').
    :param quality: Kualitas kompresi (1-100), relevan untuk JPEG.
    :param allow_overwrite: Jika False, nama file otomatis diberi sufiks unik jika sudah ada.
    :return: Path final file yang berhasil disimpan.
    """
    target = output_path if allow_overwrite else get_unique_filepath(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Buat nama file temporer di folder yang sama agar replace bersifat atomic pada partisi yang sama
    temp_filename = f".tmp_{os.getpid()}_{time.time_ns()}_{target.name}"
    temp_path = target.parent / temp_filename

    fmt = export_format.upper()
    if fmt == "JPG":
        fmt = "JPEG"

    try:
        if fmt == "JPEG":
            # JPEG tidak mendukung transparansi; blend dengan latar belakang putih
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                bg = Image.new("RGB", image.size, (255, 255, 255))
                # Gunakan alpha channel sebagai mask jika ada
                alpha_channel = image.split()[3] if image.mode == "RGBA" else None
                bg.paste(image, mask=alpha_channel)
                bg.save(temp_path, format="JPEG", quality=quality, optimize=True)
            else:
                image.convert("RGB").save(temp_path, format="JPEG", quality=quality, optimize=True)
        else:
            # Simpan dalam format PNG (mempertahankan transparansi penuh)
            image.save(temp_path, format="PNG", optimize=True)

        # Atomic replace ke file target akhir
        temp_path.replace(target)
        logger.debug("Citra berhasil disimpan secara aman ke: %s", target)
        return target

    except Exception as exc:
        # Bersihkan file temporer jika gagal
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise IOError(f"Gagal menyimpan citra ke {target}: {exc}") from exc
