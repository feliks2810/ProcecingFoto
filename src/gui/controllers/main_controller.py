"""
Controller utama untuk menghubungkan antarmuka CustomTkinter dengan BatchPipelineRunner.
Mengelola background thread, komunikasi aman lintas thread, validasi, dan pembatalan.
"""

import threading
from pathlib import Path
from typing import Optional
import customtkinter as ctk
from tkinter import messagebox

from src.config.models import BatchConfig, SingleBatchConfig
from src.pipeline.runner import BatchPipelineRunner
from src.pipeline.reporter import PipelineReport


class MainAppController:
    """
    Controller yang mengelola alur logika bisnis GUI, validasi input,
    eksekusi background worker, dan pengiriman event ke main thread Tkinter.
    """

    def __init__(
        self,
        root: ctk.CTk,
        config: BatchConfig,
        on_progress_ui: Optional[callable] = None,
        on_log_ui: Optional[callable] = None,
        on_state_change: Optional[callable] = None
    ):
        self.root = root
        self.config = config
        self.on_progress_ui = on_progress_ui
        self.on_log_ui = on_log_ui
        self.on_state_change = on_state_change

        self._is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()
        self._last_report: Optional[PipelineReport] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _dispatch(self, func, *args) -> None:
        """Memastikan fungsi dipanggil di thread utama Tkinter secara aman."""
        if func:
            self.root.after(0, func, *args)

    def validate_configuration(self) -> tuple[bool, str]:
        """
        Memvalidasi kesiapan parameter kedua batch sebelum eksekusi dimulai.
        """
        # Periksa minimal 1 batch memiliki folder dan frame
        has_at_least_one = False
        for b in (self.config.batch_1, self.config.batch_2):
            if b.input_folder and b.frame_path:
                has_at_least_one = True
                if not b.input_folder.is_dir():
                    return False, f"Folder foto untuk {b.name} tidak valid: {b.input_folder}"
                if not b.frame_path.is_file():
                    return False, f"File frame PNG untuk {b.name} tidak ditemukan: {b.frame_path}"
                if not b.slot_coordinates:
                    return False, f"Area slot foto untuk {b.name} belum ditentukan. Silakan buka Editor."

        if not has_at_least_one:
            return False, "Harap lengkapi folder foto dan frame PNG untuk setidaknya satu batch."

        if not self.config.output_folder:
            return False, "Folder output belum ditentukan."

        return True, "Konfigurasi valid."

    def start_batch_processing(self) -> None:
        """
        Memulai proses batch pemrosesan citra dalam background thread.
        Mencegah eksekusi ganda jika proses sedang berlangsung.
        """
        if self._is_running:
            messagebox.showwarning("Proses Berjalan", "Pemrosesan batch sedang berlangsung!")
            return

        is_valid, msg = self.validate_configuration()
        if not is_valid:
            messagebox.showwarning("Konfigurasi Belum Lengkap", msg)
            return

        self._is_running = True
        self._cancel_event.clear()

        if self.on_state_change:
            self.on_state_change(True)

        if self.on_log_ui:
            self.on_log_ui("=== MEMULAI PEMROSESAN BATCH 500 FOTO ===")

        # Jalankan background thread
        self._worker_thread = threading.Thread(
            target=self._run_pipeline_worker,
            daemon=True,
            name="BatchPipelineWorker"
        )
        self._worker_thread.start()

    def cancel_processing(self) -> None:
        """Mengirim sinyal pembatalan ke background worker."""
        if not self._is_running:
            return
        self._cancel_event.set()
        if self.on_log_ui:
            self.on_log_ui("Mengirim sinyal pembatalan...")

    def _run_pipeline_worker(self) -> None:
        """Fungsi yang berjalan di background thread terpisah."""
        try:
            runner = BatchPipelineRunner(
                config=self.config,
                on_progress=lambda c, t, s, f, fn, eta: self._dispatch(self.on_progress_ui, c, t, s, f, fn, eta),
                on_log=lambda m: self._dispatch(self.on_log_ui, m),
                cancel_event=self._cancel_event
            )

            report = runner.run()
            self._last_report = report

            # Ekspor laporan otomatis ke folder output
            try:
                out_dir = self.config.output_folder
                report_json = out_dir / "processing_report.json"
                report_csv = out_dir / "processing_report.csv"
                report.export_json(report_json)
                report.export_csv(report_csv)
                self._dispatch(self.on_log_ui, f"Laporan disimpan: {report_json.name} & {report_csv.name}")
            except Exception as exc:
                self._dispatch(self.on_log_ui, f"Gagal mengekspor laporan: {exc}")

            # Notifikasi penyelesaian di main thread
            self._dispatch(self._on_worker_finished, report)

        except Exception as exc:
            self._dispatch(self.on_log_ui, f"FATAL ERROR dalam worker: {exc}")
            self._dispatch(self._on_worker_finished, None)

    def _on_worker_finished(self, report: Optional[PipelineReport]) -> None:
        """Dipanggil kembali di main GUI thread saat worker selesai."""
        self._is_running = False

        if self.on_state_change:
            self.on_state_change(False)

        if report is None:
            messagebox.showerror("Error", "Terjadi kegagalan kritis saat menjalankan pemrosesan batch.")
            return

        if report.is_cancelled:
            if self.on_log_ui:
                self.on_log_ui("Pemrosesan batch telah dibatalkan oleh pengguna.")
            messagebox.showinfo("Proses Dibatalkan", f"Pemrosesan dihentikan. Berhasil memproses {report.total_success} foto.")
        else:
            summary_msg = (
                f"Pemrosesan batch selesai!\n\n"
                f"• Total Foto Ditemukan: {report.total_found}\n"
                f"• Berhasil Diproses: {report.total_success}\n"
                f"• Gagal: {report.total_failed}\n"
                f"• Durasi: {report.total_duration_seconds:.2f} detik\n"
                f"• Rata-rata Throughput: {report.overall_throughput_fps:.2f} foto/detik\n\n"
                f"Hasil disimpan di: {self.config.output_folder}"
            )
            if self.on_log_ui:
                self.on_log_ui(f"SELESAI! Sukses: {report.total_success}, Gagal: {report.total_failed} ({report.total_duration_seconds:.2f}s)")
            messagebox.showinfo("Batch Selesai", summary_msg)
