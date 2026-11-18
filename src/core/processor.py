"""
Modul pemrosesan satu foto (single photo processing orchestrator).
"""

import time
from pathlib import Path
from typing import Optional
import logging

from src.config.models import FileResult, SlotCoordinates
from src.core.validator import (
    load_frame_image,
    load_photo_image,
    validate_frame_path,
    validate_photo_path,
)
from src.core.exif_handler import normalize_exif_orientation
from src.core.compositor import compose_frame_with_photo
from src.core.writer import save_image_safely

logger = logging.getLogger(__name__)


def process_single_photo(
    photo_path: Path,
    frame_path: Path,
    slot: SlotCoordinates,
    output_dir: Path,
    output_filename: Optional[str] = None,
    export_format: str = "PNG",
    quality: int = 95,
    batch_id: str = "single",
    allow_overwrite: bool = False
) -> FileResult:
    """
    Memproses satu file foto dengan template frame PNG secara non-destructive.

    Alur Proses:
    1. Validasi keberadaan dan format file foto serta frame.
    2. Pembacaan citra ke memori.
    3. Koreksi orientasi fisik foto berdasarkan EXIF metadata.
    4. Transformasi crop & resize (Aspect Fill) presisi ke dimensi SlotCoordinates.
    5. Alpha compositing: foto di layer bawah, frame PNG di layer teratas.
    6. Penyimpanan aman (atomic write) ke output_dir tanpa menimpa file yang sudah ada.

    :param photo_path: Path file foto sumber (hanya dibaca, tidak pernah diubah).
    :param frame_path: Path file frame PNG transparan.
    :param slot: Model SlotCoordinates posisi target foto pada kanvas frame.
    :param output_dir: Direktori tempat menyimpan file hasil.
    :param output_filename: Nama file output kustom opsional.
    :param export_format: Format file akhir ('PNG' atau 'JPEG').
    :param quality: Kualitas kompresi jika format JPEG (1-100).
    :param batch_id: Identifier batch untuk pelaporan.
    :param allow_overwrite: Jika False, nama file otomatis di-resolve agar tidak menimpa file lama.
    :return: FileResult berisi status keberhasilan, path output, atau pesan error.
    """
    start_time = time.perf_counter()
    photo_path = Path(photo_path)
    frame_path = Path(frame_path)
    output_dir = Path(output_dir)

    try:
        # 1. Validasi awal jalur file
        validate_photo_path(photo_path)
        validate_frame_path(frame_path)

        # 2. Muat citra foto & frame
        photo_img = load_photo_image(photo_path)
        frame_img = load_frame_image(frame_path)

        # 3. Normalisasi orientasi EXIF
        photo_normalized = normalize_exif_orientation(photo_img)

        # 4. Penggabungan komposit citra dengan frame
        composite_result = compose_frame_with_photo(frame_img, photo_normalized, slot)

        # 5. Tentukan nama target output
        ext = export_format.lower()
        if ext == "jpeg":
            ext = "jpg"
        final_filename = output_filename or f"{photo_path.stem}_framed.{ext}"
        target_path = output_dir / final_filename

        # 6. Simpan hasil secara atomic & collision-safe
        saved_path = save_image_safely(
            image=composite_result,
            output_path=target_path,
            export_format=export_format,
            quality=quality,
            allow_overwrite=allow_overwrite
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            "Sukses memproses foto [%s] -> [%s] dalam %.2f ms",
            photo_path.name,
            saved_path.name,
            elapsed_ms
        )

        return FileResult(
            source_file=photo_path,
            output_file=saved_path,
            batch_id=batch_id,
            success=True,
            execution_time_ms=round(elapsed_ms, 2)
        )

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        err_msg = str(exc)
        logger.error(
            "Gagal memproses foto [%s]: %s (durasi: %.2f ms)",
            photo_path.name,
            err_msg,
            elapsed_ms,
            exc_info=True
        )

        return FileResult(
            source_file=photo_path,
            output_file=None,
            batch_id=batch_id,
            success=False,
            error_message=err_msg,
            execution_time_ms=round(elapsed_ms, 2)
        )
