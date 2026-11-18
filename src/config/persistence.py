"""
Modul persistensi konfigurasi pengguna (menyimpan dan memuat user_config.json).
"""

import json
from pathlib import Path
from typing import Optional
import logging

from src.config.settings import BASE_DIR
from src.config.models import BatchConfig

logger = logging.getLogger(__name__)

DEFAULT_USER_CONFIG_PATH = BASE_DIR / "user_config.json"


def save_user_config(config: BatchConfig, file_path: Path = DEFAULT_USER_CONFIG_PATH) -> bool:
    """
    Menyimpan konfigurasi BatchConfig ke dalam file JSON lokal.
    Menggunakan penulisan atomic (.tmp_... -> replace) agar file tidak korup.
    """
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target.with_suffix(".tmp_cfg")

    try:
        json_data = config.model_dump_json(indent=2)
        temp_target.write_text(json_data, encoding="utf-8")
        temp_target.replace(target)
        logger.info("Konfigurasi pengguna berhasil disimpan ke: %s", target)
        return True
    except Exception as exc:
        logger.error("Gagal menyimpan konfigurasi ke %s: %s", target, exc)
        if temp_target.exists():
            try:
                temp_target.unlink()
            except OSError:
                pass
        return False


def load_user_config(file_path: Path = DEFAULT_USER_CONFIG_PATH) -> Optional[BatchConfig]:
    """
    Membaca dan memvalidasi konfigurasi pengguna dari file JSON lokal.
    Mengembalikan instance BatchConfig yang valid, atau None jika file belum ada/tidak valid.
    """
    target = Path(file_path)
    if not target.exists() or not target.is_file():
        logger.debug("File konfigurasi lokal belum ada: %s", target)
        return None

    try:
        content = target.read_text(encoding="utf-8")
        # Validasi struktur data menggunakan Pydantic
        config = BatchConfig.model_validate_json(content)
        logger.info("Berhasil memuat konfigurasi pengguna dari: %s", target)
        return config
    except Exception as exc:
        logger.warning(
            "File konfigurasi %s tidak valid atau rusak (%s). Menggunakan konfigurasi default.",
            target.name,
            exc
        )
        return None
