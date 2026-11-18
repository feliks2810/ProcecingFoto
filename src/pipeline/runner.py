"""
Modul eksekutor batch processing pipeline untuk PhotoFrameProcessor.
Mendukung dual batch, fault-tolerance, pelacakan progress, ETA, dan pembatalan aman.
"""

import threading
import time
from pathlib import Path
from typing import Callable, List, Optional
import logging

from src.config.models import BatchConfig, FileResult, SingleBatchConfig, SlotCoordinates
from src.core.processor import process_single_photo
from src.pipeline.scanner import scan_folder_photos
from src.pipeline.reporter import BatchBreakdown, PipelineReport

logger = logging.getLogger(__name__)

# Tipe callback progress untuk antarmuka GUI atau CLI
# on_progress(completed, total, success, failed, current_filename, eta_seconds)
ProgressCallback = Callable[[int, int, int, int, str, Optional[float]], None]
LogCallback = Callable[[str], None]


def cleanup_stray_temp_files(directory: Path) -> None:
    """
    Membersihkan file temporer (.tmp_*) yang mungkin tertinggal jika terjadi interupsi.
    """
    if not directory.exists() or not directory.is_dir():
        return
    try:
        for p in directory.glob(".tmp_*"):
            try:
                if p.is_file():
                    p.unlink()
            except OSError:
                pass
    except Exception as exc:
        logger.debug("Tidak dapat membersihkan file temporer di %s: %s", directory, exc)


class BatchPipelineRunner:
    """
    Eksekutor pipeline pemrosesan citra batch (Batch 1 dan Batch 2).
    """

    def __init__(
        self,
        config: BatchConfig,
        on_progress: Optional[ProgressCallback] = None,
        on_log: Optional[LogCallback] = None,
        cancel_event: Optional[threading.Event] = None
    ):
        self.config = config
        self.on_progress = on_progress
        self.on_log = on_log
        self.cancel_event = cancel_event or threading.Event()

    def _log(self, message: str) -> None:
        logger.info(message)
        if self.on_log:
            self.on_log(message)

    def cancel(self) -> None:
        """Mengirim sinyal pembatalan ke pipeline yang sedang berjalan."""
        self.cancel_event.set()
        self._log("Sinyal pembatalan diterima. Menghentikan pemrosesan batch...")

    def run(self) -> PipelineReport:
        """
        Menjalankan seluruh alur pemrosesan batch 1 dan batch 2 secara sekuensial.
        Mengembalikan PipelineReport lengkap.
        """
        overall_start_time = time.perf_counter()
        report = PipelineReport()

        # 1. Pindai file foto untuk kedua batch
        batch_tasks: List[tuple[SingleBatchConfig, List[Path]]] = []
        total_photos_all = 0

        for b_config in (self.config.batch_1, self.config.batch_2):
            if b_config.input_folder and b_config.input_folder.exists():
                scanned = scan_folder_photos(b_config.input_folder, max_photos=b_config.max_photos)
            else:
                scanned = []
                self._log(f"Peringatan: Folder input untuk {b_config.name} tidak valid atau belum diatur.")

            batch_tasks.append((b_config, scanned))
            total_photos_all += len(scanned)

        report.total_found = total_photos_all
        self._log(f"Memulai pipeline: total {total_photos_all} foto siap diproses dalam 2 batch.")

        if total_photos_all == 0:
            self._log("Tidak ada foto yang ditemukan untuk diproses. Pipeline selesai.")
            report.total_duration_seconds = time.perf_counter() - overall_start_time
            return report

        completed_photos = 0
        total_success = 0
        total_failed = 0

        # 2. Proses tiap batch
        for b_config, file_list in batch_tasks:
            if self.cancel_event.is_set():
                report.is_cancelled = True
                self._log("Proses dibatalkan sebelum memulai batch berikutnya.")
                break

            out_dir = self.config.get_output_dir_for_batch(b_config.batch_id)
            out_dir.mkdir(parents=True, exist_ok=True)

            breakdown = BatchBreakdown(
                batch_id=b_config.batch_id,
                name=b_config.name,
                input_folder=str(b_config.input_folder) if b_config.input_folder else None,
                frame_path=str(b_config.frame_path) if b_config.frame_path else None,
                output_folder=str(out_dir),
                total_found=len(file_list)
            )

            if not file_list:
                report.batches[b_config.batch_id] = breakdown
                continue

            if not b_config.frame_path or not b_config.frame_path.exists():
                err_msg = f"Frame PNG untuk {b_config.name} tidak ditemukan: {b_config.frame_path}"
                self._log(f"ERROR: {err_msg}")
                # Tandai seluruh file dalam batch ini sebagai gagal
                for f in file_list:
                    res = FileResult(
                        source_file=f,
                        batch_id=b_config.batch_id,
                        success=False,
                        error_message=err_msg
                    )
                    report.results.append(res)
                    total_failed += 1
                    completed_photos += 1
                    breakdown.failed_items.append({"file": f.name, "reason": err_msg})
                breakdown.total_processed = len(file_list)
                breakdown.total_failed = len(file_list)
                report.batches[b_config.batch_id] = breakdown
                continue

            # Gunakan slot koordinat yang dikonfigurasi, atau dimensi default
            slot = b_config.slot_coordinates
            if slot is None:
                err_msg = f"SlotCoordinates untuk {b_config.name} belum ditentukan."
                self._log(f"ERROR: {err_msg}")
                for f in file_list:
                    res = FileResult(
                        source_file=f,
                        batch_id=b_config.batch_id,
                        success=False,
                        error_message=err_msg
                    )
                    report.results.append(res)
                    total_failed += 1
                    completed_photos += 1
                    breakdown.failed_items.append({"file": f.name, "reason": err_msg})
                breakdown.total_processed = len(file_list)
                breakdown.total_failed = len(file_list)
                report.batches[b_config.batch_id] = breakdown
                continue

            batch_start_time = time.perf_counter()
            self._log(f"--- Menjalankan {b_config.name}: {len(file_list)} foto ---")

            # Eksekusi foto satu demi satu
            for photo_path in file_list:
                if self.cancel_event.is_set():
                    report.is_cancelled = True
                    self._log("Proses dibatalkan di tengah eksekusi batch.")
                    # Bersihkan file temporer jika ada
                    cleanup_stray_temp_files(out_dir)
                    break

                # Panggil core engine process_single_photo
                file_result = process_single_photo(
                    photo_path=photo_path,
                    frame_path=b_config.frame_path,
                    slot=slot,
                    output_dir=out_dir,
                    export_format=self.config.export_format,
                    quality=self.config.output_quality,
                    batch_id=b_config.batch_id,
                    allow_overwrite=False
                )

                completed_photos += 1
                if file_result.success:
                    total_success += 1
                    breakdown.total_success += 1
                else:
                    total_failed += 1
                    breakdown.total_failed += 1
                    breakdown.failed_items.append({
                        "file": photo_path.name,
                        "reason": file_result.error_message or "Unknown error"
                    })

                report.results.append(file_result)

                # Hitung estimasi sisa waktu (ETA)
                elapsed_now = time.perf_counter() - overall_start_time
                avg_time = elapsed_now / completed_photos if completed_photos > 0 else 0
                remaining = total_photos_all - completed_photos
                eta_sec = remaining * avg_time if remaining > 0 else 0.0

                if self.on_progress:
                    self.on_progress(
                        completed_photos,
                        total_photos_all,
                        total_success,
                        total_failed,
                        photo_path.name,
                        eta_sec
                    )

            batch_duration = time.perf_counter() - batch_start_time
            breakdown.total_processed = breakdown.total_success + breakdown.total_failed
            breakdown.duration_seconds = batch_duration
            if breakdown.total_processed > 0:
                breakdown.avg_ms_per_photo = (batch_duration * 1000.0) / breakdown.total_processed
            report.batches[b_config.batch_id] = breakdown

        # Finalisasi metrik laporan
        overall_duration = time.perf_counter() - overall_start_time
        report.total_processed = completed_photos
        report.total_success = total_success
        report.total_failed = total_failed
        report.total_duration_seconds = overall_duration
        if completed_photos > 0:
            report.avg_ms_per_photo = (overall_duration * 1000.0) / completed_photos
            report.overall_throughput_fps = completed_photos / overall_duration if overall_duration > 0 else 0.0

        self._log(
            f"Pipeline selesai dalam {overall_duration:.2f} detik. "
            f"Sukses: {total_success}, Gagal: {total_failed}, "
            f"Throughput: {report.overall_throughput_fps:.2f} foto/detik."
        )

        return report
