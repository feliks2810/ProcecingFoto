"""
Modul validasi dan pembacaan file citra serta frame untuk PhotoFrameProcessor.
"""

from pathlib import Path
from typing import Optional
from PIL import Image, ImageFile
import logging

from src.config.settings import SUPPORTED_FRAME_EXTENSIONS, SUPPORTED_PHOTO_EXTENSIONS

# Izinkan pembacaan gambar dengan potongan minor
ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)


class ImageValidationError(Exception):
    """Pengecualian saat validasi file citra gagal."""
    pass


def validate_photo_path(photo_path: Path) -> Path:
    """
    Memvalidasi keberadaan dan format ekstensi file foto.
    """
    if not isinstance(photo_path, Path):
        photo_path = Path(photo_path)

    if not photo_path.exists():
        raise FileNotFoundError(f"File foto tidak ditemukan: {photo_path}")

    if not photo_path.is_file():
        raise ImageValidationError(f"Jalur foto bukan sebuah file: {photo_path}")

    if photo_path.stat().st_size == 0:
        raise ImageValidationError(f"File foto kosong (0 byte): {photo_path}")

    if photo_path.suffix.lower() not in SUPPORTED_PHOTO_EXTENSIONS:
        raise ImageValidationError(
            f"Ekstensi foto '{photo_path.suffix}' tidak didukung. "
            f"Format yang didukung: {sorted(SUPPORTED_PHOTO_EXTENSIONS)}"
        )

    return photo_path


def validate_frame_path(frame_path: Path) -> Path:
    """
    Memvalidasi keberadaan dan format file frame PNG.
    """
    if not isinstance(frame_path, Path):
        frame_path = Path(frame_path)

    if not frame_path.exists():
        raise FileNotFoundError(f"File frame tidak ditemukan: {frame_path}")

    if not frame_path.is_file():
        raise ImageValidationError(f"Jalur frame bukan sebuah file: {frame_path}")

    if frame_path.stat().st_size == 0:
        raise ImageValidationError(f"File frame kosong (0 byte): {frame_path}")

    if frame_path.suffix.lower() not in SUPPORTED_FRAME_EXTENSIONS:
        raise ImageValidationError(
            f"Frame harus berformat PNG transparan ({SUPPORTED_FRAME_EXTENSIONS}), "
            f"format ditemukan: {frame_path.suffix}"
        )

    return frame_path


def load_photo_image(photo_path: Path) -> Image.Image:
    """
    Membaca dan memverifikasi integritas file foto menggunakan Pillow.
    Mengembalikan salinan objek Image yang terlepas dari file descriptor.
    """
    valid_path = validate_photo_path(photo_path)
    try:
        with Image.open(valid_path) as raw_img:
            # Memuat data piksel ke memori sebelum file descriptor ditutup
            raw_img.load()
            # Salin citra agar independen dari handler file
            return raw_img.copy()
    except Exception as exc:
        raise ImageValidationError(f"Gagal membaca atau mendekode file foto {photo_path.name}: {exc}") from exc


def load_frame_image(frame_path: Path) -> Image.Image:
    """
    Membaca dan memvalidasi frame PNG serta memastikan mode RGBA untuk saluran alpha.
    """
    valid_path = validate_frame_path(frame_path)
    try:
        with Image.open(valid_path) as raw_frame:
            raw_frame.load()
            frame_copy = raw_frame.copy()

        if frame_copy.mode != "RGBA":
            # Konversi jika format PNG palletized dengan transparansi (P / L)
            frame_copy = frame_copy.convert("RGBA")

        return frame_copy
    except Exception as exc:
        raise ImageValidationError(f"Gagal membaca atau memproses frame PNG {frame_path.name}: {exc}") from exc
