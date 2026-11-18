"""
Panel progres, status eksekusi, kontrol pembatalan, dan folder output.
"""

import os
from pathlib import Path
from typing import Callable, Optional
import customtkinter as ctk
from tkinter import filedialog


class ProgressControlPanel(ctk.CTkFrame):
    """
    Panel kontrol utama: pemilihan folder output, tombol eksekusi,
    progress bar, counter statistik, dan tombol pembatalan.
    """

    def __init__(
        self,
        master,
        default_output_dir: Path,
        on_start_process: Callable[[], None],
        on_cancel_process: Callable[[], None],
        on_output_changed: Optional[Callable[[Path], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.output_dir = default_output_dir
        self.on_start_process = on_start_process
        self.on_cancel_process = on_cancel_process
        self.on_output_changed = on_output_changed

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        # 1. Baris Pemilihan Folder Output
        lbl_out = ctk.CTkLabel(self, text="Folder Output Hasil:", width=140, anchor="w")
        lbl_out.grid(row=0, column=0, padx=(15, 5), pady=(12, 6), sticky="w")

        self.entry_out = ctk.CTkEntry(self, placeholder_text="Pilih folder tujuan penyimpanan...")
        self.entry_out.grid(row=0, column=1, padx=5, pady=(12, 6), sticky="ew")
        self.entry_out.insert(0, str(self.output_dir))

        btn_browse_out = ctk.CTkButton(
            self,
            text="Pilih Folder",
            width=100,
            command=self._on_browse_output
        )
        btn_browse_out.grid(row=0, column=2, padx=(5, 15), pady=(12, 6))

        # 2. Progress Bar & Persentase
        self.progress_bar = ctk.CTkProgressBar(self, height=16)
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=(15, 10), pady=(12, 6), sticky="ew")
        self.progress_bar.set(0.0)

        self.lbl_percentage = ctk.CTkLabel(
            self,
            text="0%",
            width=50,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_percentage.grid(row=1, column=2, padx=(0, 15), pady=(12, 6))

        # 3. Baris Status & Counter
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=2, column=0, columnspan=3, padx=15, pady=4, sticky="ew")

        self.lbl_status_counts = ctk.CTkLabel(
            status_frame,
            text="Siap | Sukses: 0 | Gagal: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#81C784"
        )
        self.lbl_status_counts.pack(side="left")

        self.lbl_eta = ctk.CTkLabel(
            status_frame,
            text="Estimasi Sisa Waktu: -",
            font=ctk.CTkFont(size=12),
            text_color="#B0BEC5"
        )
        self.lbl_eta.pack(side="right")

        self.lbl_current_file = ctk.CTkLabel(
            self,
            text="Menunggu instruksi pengguna...",
            font=ctk.CTkFont(size=12),
            text_color="#90A4AE",
            anchor="w"
        )
        self.lbl_current_file.grid(row=3, column=0, columnspan=3, padx=15, pady=(0, 10), sticky="w")

        # 4. Tombol Aksi Utama
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=4, column=0, columnspan=3, padx=15, pady=(6, 12), sticky="ew")

        self.btn_process = ctk.CTkButton(
            action_frame,
            text="Mulai Proses 500 Foto",
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.on_start_process
        )
        self.btn_process.pack(side="left", padx=(0, 12), fill="x", expand=True)

        self.btn_cancel = ctk.CTkButton(
            action_frame,
            text="Batal",
            fg_color="#C62828",
            hover_color="#B71C1C",
            height=40,
            width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self.on_cancel_process
        )
        self.btn_cancel.pack(side="left", padx=(0, 12))

        self.btn_open_out = ctk.CTkButton(
            action_frame,
            text="Buka Folder Hasil",
            fg_color="#37474F",
            hover_color="#263238",
            height=40,
            width=140,
            command=self._on_open_output_folder
        )
        self.btn_open_out.pack(side="right")

    def _on_browse_output(self) -> None:
        folder = filedialog.askdirectory(title="Pilih Folder Output Hasil Komposit")
        if folder:
            p = Path(folder)
            self.output_dir = p
            self.entry_out.delete(0, "end")
            self.entry_out.insert(0, str(p))
            if self.on_output_changed:
                self.on_output_changed(p)

    def _on_open_output_folder(self) -> None:
        """Membuka folder output di Windows Explorer."""
        p = self.get_output_dir()
        if p.exists():
            os.startfile(str(p))
        else:
            p.mkdir(parents=True, exist_ok=True)
            os.startfile(str(p))

    def get_output_dir(self) -> Path:
        val = self.entry_out.get().strip()
        if val:
            return Path(val)
        return self.output_dir

    def set_processing_state(self, is_processing: bool) -> None:
        """Mengatur status aktif tombol saat proses berjalan atau selesai."""
        if is_processing:
            self.btn_process.configure(state="disabled")
            self.btn_cancel.configure(state="normal")
        else:
            self.btn_process.configure(state="normal")
            self.btn_cancel.configure(state="disabled")

    def update_progress(
        self,
        completed: int,
        total: int,
        success: int,
        failed: int,
        current_file: str,
        eta_sec: Optional[float]
    ) -> None:
        ratio = completed / total if total > 0 else 0.0
        self.progress_bar.set(ratio)
        self.lbl_percentage.configure(text=f"{int(ratio * 100)}%")

        self.lbl_status_counts.configure(
            text=f"Memproses [{completed}/{total}] | Sukses: {success} | Gagal: {failed}",
            text_color="#81C784" if failed == 0 else "#FFB74D"
        )

        if eta_sec is not None and eta_sec > 0:
            if eta_sec < 60:
                eta_str = f"{int(eta_sec)} detik"
            else:
                eta_str = f"{int(eta_sec // 60)} menit {int(eta_sec % 60)} detik"
            self.lbl_eta.configure(text=f"Sisa Waktu: ~{eta_str}")
        else:
            self.lbl_eta.configure(text="Sisa Waktu: Selesai" if completed >= total else "Sisa Waktu: Menghitung...")

        self.lbl_current_file.configure(text=f"Sedang memproses: {current_file}")
