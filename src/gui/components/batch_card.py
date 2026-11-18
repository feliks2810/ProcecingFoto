"""
Komponen kartu konfigurasi batch (Batch 1 & Batch 2).
"""

from pathlib import Path
from typing import Callable, Optional
import customtkinter as ctk
from tkinter import filedialog, messagebox

from src.config.models import SingleBatchConfig, SlotCoordinates
from src.core.validator import load_frame_image
from src.pipeline.scanner import scan_folder_photos
from src.gui.components.placement_editor import PhotoPlacementEditor


class BatchConfigCard(ctk.CTkFrame):
    """
    Kartu antarmuka untuk mengatur folder foto sumber, file frame PNG,
    dan koordinat slot penempatan foto untuk satu batch.
    """

    def __init__(
        self,
        master,
        batch_id: str,
        title: str,
        initial_config: SingleBatchConfig,
        on_config_changed: Optional[Callable[[], None]] = None,
        on_preview_requested: Optional[Callable[[SingleBatchConfig], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.batch_id = batch_id
        self.title_text = title
        self.batch_config = initial_config
        self.on_config_changed = on_config_changed
        self.on_preview_requested = on_preview_requested

        self._build_ui()
        self._refresh_display()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        # Header Title
        self.title_lbl = ctk.CTkLabel(
            self,
            text=self.title_text,
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.title_lbl.grid(row=0, column=0, columnspan=3, padx=15, pady=(12, 8), sticky="w")

        # 1. Baris Pemilihan Folder Foto
        lbl_folder = ctk.CTkLabel(self, text="Folder Foto Sumber:", width=140, anchor="w")
        lbl_folder.grid(row=1, column=0, padx=(15, 5), pady=6, sticky="w")

        self.entry_folder = ctk.CTkEntry(self, placeholder_text="Pilih folder berisi foto...")
        self.entry_folder.grid(row=1, column=1, padx=5, pady=6, sticky="ew")

        btn_browse_folder = ctk.CTkButton(
            self,
            text="Pilih Folder",
            width=100,
            command=self._on_browse_folder
        )
        btn_browse_folder.grid(row=1, column=2, padx=(5, 15), pady=6)

        # Status jumlah foto ditemukan
        self.lbl_photos_count = ctk.CTkLabel(
            self,
            text="Foto ditemukan: 0 file",
            font=ctk.CTkFont(size=12),
            text_color="#90CAF9"
        )
        self.lbl_photos_count.grid(row=2, column=1, padx=5, pady=(0, 6), sticky="w")

        # 2. Baris Pemilihan Frame PNG
        lbl_frame = ctk.CTkLabel(self, text="Desain Frame PNG:", width=140, anchor="w")
        lbl_frame.grid(row=3, column=0, padx=(15, 5), pady=6, sticky="w")

        self.entry_frame = ctk.CTkEntry(self, placeholder_text="Pilih file frame PNG transparan...")
        self.entry_frame.grid(row=3, column=1, padx=5, pady=6, sticky="ew")

        btn_browse_frame = ctk.CTkButton(
            self,
            text="Pilih Frame",
            width=100,
            command=self._on_browse_frame
        )
        btn_browse_frame.grid(row=3, column=2, padx=(5, 15), pady=6)

        # Status resolusi frame
        self.lbl_frame_info = ctk.CTkLabel(
            self,
            text="Resolusi Frame: Belum dipilih",
            font=ctk.CTkFont(size=12),
            text_color="#A5D6A7"
        )
        self.lbl_frame_info.grid(row=4, column=1, padx=5, pady=(0, 6), sticky="w")

        # 3. Baris Info Koordinat Slot & Tombol Aksi
        self.lbl_slot_info = ctk.CTkLabel(
            self,
            text="Area Foto (Slot): Belum diatur",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FFE082"
        )
        self.lbl_slot_info.grid(row=5, column=0, columnspan=2, padx=15, pady=8, sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=3, padx=15, pady=(6, 12), sticky="ew")

        self.btn_open_editor = ctk.CTkButton(
            btn_frame,
            text="Atur Area Foto (Editor)",
            fg_color="#00838F",
            hover_color="#006064",
            command=self._on_open_placement_editor
        )
        self.btn_open_editor.pack(side="left", padx=(0, 10))

        self.btn_preview = ctk.CTkButton(
            btn_frame,
            text="Lihat Preview",
            fg_color="#37474F",
            hover_color="#263238",
            command=self._on_preview_click
        )
        self.btn_preview.pack(side="left")

    def _on_browse_folder(self) -> None:
        folder = filedialog.askdirectory(title=f"Pilih Folder Foto - {self.title_text}")
        if folder:
            p = Path(folder)
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, str(p))
            self.batch_config.input_folder = p
            self._update_photo_count()
            if self.on_config_changed:
                self.on_config_changed()

    def _update_photo_count(self) -> None:
        if self.batch_config.input_folder and self.batch_config.input_folder.is_dir():
            try:
                photos = scan_folder_photos(self.batch_config.input_folder, max_photos=self.batch_config.max_photos)
                count = len(photos)
                self.lbl_photos_count.configure(
                    text=f"Foto ditemukan: {count} file (siap diproses)",
                    text_color="#81C784" if count > 0 else "#EF9A9A"
                )
            except Exception as exc:
                self.lbl_photos_count.configure(text=f"Error membaca folder: {exc}", text_color="#E57373")
        else:
            self.lbl_photos_count.configure(text="Foto ditemukan: 0 file", text_color="#90CAF9")

    def _on_browse_frame(self) -> None:
        frame_file = filedialog.askopenfilename(
            title=f"Pilih Frame PNG - {self.title_text}",
            filetypes=[("PNG Transparent Frame", "*.png"), ("All Files", "*.*")]
        )
        if frame_file:
            p = Path(frame_file)
            self.entry_frame.delete(0, "end")
            self.entry_frame.insert(0, str(p))
            self.batch_config.frame_path = p
            self._update_frame_info()
            if self.on_config_changed:
                self.on_config_changed()

    def _update_frame_info(self) -> None:
        if self.batch_config.frame_path and self.batch_config.frame_path.is_file():
            try:
                img = load_frame_image(self.batch_config.frame_path)
                w, h = img.size
                self.lbl_frame_info.configure(
                    text=f"Resolusi Frame: {w} x {h} px (RGBA)",
                    text_color="#81C784"
                )
                # Jika slot belum diatur, beri default 70% di tengah
                if not self.batch_config.slot_coordinates:
                    sw = int(w * 0.7)
                    sh = int(h * 0.7)
                    sx = (w - sw) // 2
                    sy = (h - sh) // 2
                    self.batch_config.slot_coordinates = SlotCoordinates(x=sx, y=sy, width=sw, height=sh)
                self._update_slot_label()
            except Exception as exc:
                self.lbl_frame_info.configure(text=f"Error membaca frame: {exc}", text_color="#E57373")
        else:
            self.lbl_frame_info.configure(text="Resolusi Frame: Belum dipilih", text_color="#A5D6A7")

    def _update_slot_label(self) -> None:
        slot = self.batch_config.slot_coordinates
        if slot:
            self.lbl_slot_info.configure(
                text=f"Area Foto (Slot): X={slot.x}, Y={slot.y}, W={slot.width}, H={slot.height} px",
                text_color="#FFE082"
            )
        else:
            self.lbl_slot_info.configure(text="Area Foto (Slot): Belum diatur", text_color="#B0BEC5")

    def _on_open_placement_editor(self) -> None:
        if not self.batch_config.frame_path or not self.batch_config.frame_path.is_file():
            messagebox.showwarning(
                "Frame Belum Dipilih",
                f"Silakan pilih file frame PNG untuk {self.title_text} terlebih dahulu sebelum membuka editor."
            )
            return

        # Ambil sampel foto pertama dari folder jika ada
        sample_path: Optional[Path] = None
        if self.batch_config.input_folder and self.batch_config.input_folder.is_dir():
            photos = scan_folder_photos(self.batch_config.input_folder, max_photos=1)
            if photos:
                sample_path = photos[0]

        def on_saved(saved_slot: SlotCoordinates):
            self.batch_config.slot_coordinates = saved_slot
            self._update_slot_label()
            if self.on_config_changed:
                self.on_config_changed()

        PhotoPlacementEditor(
            parent=self.winfo_toplevel(),
            frame_path=self.batch_config.frame_path,
            initial_slot=self.batch_config.slot_coordinates,
            sample_photo_path=sample_path,
            on_save_slot=on_saved
        )

    def _on_preview_click(self) -> None:
        if self.on_preview_requested:
            self.on_preview_requested(self.batch_config)

    def _refresh_display(self) -> None:
        if self.batch_config.input_folder:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, str(self.batch_config.input_folder))
            self._update_photo_count()
        if self.batch_config.frame_path:
            self.entry_frame.delete(0, "end")
            self.entry_frame.insert(0, str(self.batch_config.frame_path))
            self._update_frame_info()
        self._update_slot_label()
