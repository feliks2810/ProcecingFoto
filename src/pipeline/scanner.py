"""
Modul pemindaian dan penyaringan file foto sumber dalam direktori.
"""

from pathlib import Path
from typing import List, Optional, Set
import logging

from src.config.settings import DEFAULT_PHOTOS_PER_BATCH, SUPPORTED_PHOTO_EXTENSIONS

logger = logging.getLogger(__name__)


def scan_folder_photos(
    folder_path: Path,
    max_photos: int = DEFAULT_PHOTOS_PER_BATCH,
    supported_extensions: Optional[Set[str]] = None
) -> List[Path]:
    """
    Memindai folder input secara aman dan mengembalikan daftar file citra yang didukung.

    :param folder_path: Direktori yang akan dipindai.
    :param max_photos: Jumlah maksimal foto yang akan diambil (default: 250).
    :param supported_extensions: Himpunan ekstensi citra yang diizinkan (default dari settings).
    :return: Daftar Path file yang valid dan telah diurutkan sesuai abjad, dipotong maks max_photos.
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder input tidak ditemukan: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Jalur bukan sebuah direktori: {folder}")

    valid_exts = supported_extensions or SUPPORTED_PHOTO_EXTENSIONS
    valid_exts_lower = {ext.lower() for ext in valid_exts}

    found_files: List[Path] = []
    try:
        # Pindai hanya file di tingkat direktori utama
        for item in folder.iterdir():
            if item.is_file() and item.suffix.lower() in valid_exts_lower:
                found_files.append(item)
    except Exception as exc:
        logger.error("Gagal memindai direktori %s: %s", folder, exc)
        raise

    # Urutkan berdasarkan nama agar urutan pemrosesan deterministik
    found_files.sort(key=lambda p: p.name.lower())
    total_found = len(found_files)

    if total_found > max_photos:
        logger.info(
            "Folder %s memuat %d foto. Membatasi pemrosesan ke %d foto pertama.",
            folder.name,
            total_found,
            max_photos
        )
        return found_files[:max_photos]

    logger.info("Folder %s: ditemukan %d foto valid.", folder.name, total_found)
    return found_files
