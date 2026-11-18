"""
Jendela utama desktop GUI PhotoFrameProcessor berbasis CustomTkinter.
"""

from pathlib import Path
from typing import Optional
import customtkinter as ctk
from tkinter import messagebox

from src.config.settings import (
    APP_TITLE,
    BASE_DIR,
    DEMO_BORDERS_DIR,
    FINAL_BORDERS_DIR,
    GUI_APPEARANCE_MODE,
    GUI_COLOR_THEME,
    GUI_DEFAULT_WINDOW_SIZE,
    GUI_MIN_WINDOW_SIZE,
)
from src.config.models import BatchConfig, SingleBatchConfig
from src.config.persistence import load_user_config, save_user_config
from src.gui.components.batch_card import BatchConfigCard
from src.gui.components.progress_panel import ProgressControlPanel
from src.gui.components.log_console import LogConsole
from src.gui.components.preview_modal import CompositePreviewModal
from src.gui.controllers.main_controller import MainAppController


def resolve_default_frame(final_filename: str, demo_filename: str) -> Optional[Path]:
    """
    Menentukan path frame default dengan prioritas:
    1. Final frame (assets/borders/final/<final_filename>)
    2. Demo frame (assets/borders/demo/<demo_filename>)
    3. None (jika keduanya tidak tersedia)
    """
    final_path = FINAL_BORDERS_DIR / final_filename
    if final_path.exists():
        return final_path
    demo_path = DEMO_BORDERS_DIR / demo_filename
    if demo_path.exists():
        return demo_path
    return None


class PhotoFrameProcessorApp(ctk.CTk):
    """
    Aplikasi desktop utama PhotoFrameProcessor:
    - Pengaturan Batch 1 dan Batch 2 secara modular.
    - Interactive Photo Placement Editor.
    - Preview komposit sebelum pemrosesan.
    - Progress tracking real-time dan log pelaporan.
    """

    def __init__(self, initial_config: Optional[BatchConfig] = None):
        super().__init__()

        # Setup tema dan jendela
        ctk.set_appearance_mode(GUI_APPEARANCE_MODE)
        ctk.set_default_color_theme(GUI_COLOR_THEME)

        self.title(APP_TITLE)
        self.geometry(GUI_DEFAULT_WINDOW_SIZE)
        self.minsize(*GUI_MIN_WINDOW_SIZE)

        # Inisialisasi model konfigurasi (muat dari file lokal jika tersedia)
        default_out = BASE_DIR / "outputs"
        loaded_cfg = load_user_config()
        if initial_config:
            self.config = initial_config
        elif loaded_cfg:
            self.config = loaded_cfg
        else:
            default_frame_a = resolve_default_frame("frame_desain_a.png", "demo_frame_a.png")
            default_frame_b = resolve_default_frame("frame_desain_b.png", "demo_frame_b.png")

            self.config = BatchConfig(
                output_folder=default_out,
                batch_1=SingleBatchConfig(
                    batch_id="batch_1",
                    name="Batch 1 (Frame Desain A)",
                    frame_path=default_frame_a,
                    max_photos=250
                ),
                batch_2=SingleBatchConfig(
                    batch_id="batch_2",
                    name="Batch 2 (Frame Desain B)",
                    frame_path=default_frame_b,
                    max_photos=250
                )
            )

        self._build_layout()

        # Inisialisasi Controller
        self.controller = MainAppController(
            root=self,
            config=self.config,
            on_progress_ui=self.progress_panel.update_progress,
            on_log_ui=self.log_console.log,
            on_state_change=self._on_processing_state_changed
        )

        # Tangani penutupan jendela saat proses berjalan
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.log_console.log("PhotoFrameProcessor siap digunakan. Silakan atur Batch 1 dan Batch 2.")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header Bar
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#E0E0E0", "#1E1E1E"))
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)

        lbl_app_title = ctk.CTkLabel(
            header,
            text="PhotoFrameProcessor Studio",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_app_title.grid(row=0, column=0, padx=20, pady=(10, 2), sticky="w")

        lbl_app_desc = ctk.CTkLabel(
            header,
            text="Pemrosesan batch 500 foto otomatis dengan 2 desain frame PNG transparan & penempatan presisi",
            font=ctk.CTkFont(size=12),
            text_color=("#616161", "#9E9E9E")
        )
        lbl_app_desc.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # Tombol ganti tema (Light / Dark)
        self.theme_switch = ctk.CTkSwitch(
            header,
            text="Mode Gelap",
            command=self._toggle_theme
        )
        self.theme_switch.select() if ctk.get_appearance_mode() == "Dark" else self.theme_switch.deselect()
        self.theme_switch.grid(row=0, column=1, rowspan=2, padx=20, pady=10, sticky="e")

        # 2. Area Konten Utama (Scrollable atau 2 Kolom)
        main_content = ctk.CTkScrollableFrame(self)
        main_content.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        main_content.grid_columnconfigure(0, weight=1)
        main_content.grid_columnconfigure(1, weight=1)

        # Kartu Batch 1
        self.card_batch_1 = BatchConfigCard(
            main_content,
            batch_id="batch_1",
            title="Pengaturan Batch 1 (Maks 250 Foto - Frame Desain A)",
            initial_config=self.config.batch_1,
            on_config_changed=self._on_config_updated,
            on_preview_requested=self._show_preview_modal
        )
        self.card_batch_1.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="nsew")

        # Kartu Batch 2
        self.card_batch_2 = BatchConfigCard(
            main_content,
            batch_id="batch_2",
            title="Pengaturan Batch 2 (Maks 250 Foto - Frame Desain B)",
            initial_config=self.config.batch_2,
            on_config_changed=self._on_config_updated,
            on_preview_requested=self._show_preview_modal
        )
        self.card_batch_2.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="nsew")

        # 3. Panel Progres & Kontrol
        self.progress_panel = ProgressControlPanel(
            self,
            default_output_dir=self.config.output_folder,
            on_start_process=self._on_start_clicked,
            on_cancel_process=self._on_cancel_clicked,
            on_output_changed=self._on_output_changed
        )
        self.progress_panel.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        # 4. Konsol Log & Laporan Hasil
        self.log_console = LogConsole(self, height=140)
        self.log_console.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")

    def _toggle_theme(self) -> None:
        if self.theme_switch.get():
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def _on_config_updated(self) -> None:
        # Update referensi konfigurasi dan simpan ke file lokal
        self.config.batch_1 = self.card_batch_1.batch_config
        self.config.batch_2 = self.card_batch_2.batch_config
        save_user_config(self.config)

    def _on_output_changed(self, new_output: Path) -> None:
        self.config.output_folder = new_output
        save_user_config(self.config)

    def _show_preview_modal(self, batch_cfg: SingleBatchConfig) -> None:
        if not batch_cfg.frame_path or not batch_cfg.frame_path.is_file():
            messagebox.showwarning("Frame Belum Dipilih", "Silakan pilih file frame PNG terlebih dahulu.")
            return
        CompositePreviewModal(self, batch_cfg)

    def _on_start_clicked(self) -> None:
        self._on_config_updated()
        self.config.output_folder = self.progress_panel.get_output_dir()
        save_user_config(self.config)
        self.controller.start_batch_processing()

    def _on_cancel_clicked(self) -> None:
        self.controller.cancel_processing()

    def _on_processing_state_changed(self, is_processing: bool) -> None:
        self.progress_panel.set_processing_state(is_processing)

    def _on_window_close(self) -> None:
        # Simpan konfigurasi terakhir sebelum keluar
        self._on_config_updated()
        if self.controller.is_running:
            ans = messagebox.askyesno(
                "Konfirmasi Keluar",
                "Pemrosesan batch sedang berlangsung. Apakah Anda yakin ingin membatalkan dan menutup aplikasi?"
            )
            if ans:
                self.controller.cancel_processing()
                self.destroy()
        else:
            self.destroy()
