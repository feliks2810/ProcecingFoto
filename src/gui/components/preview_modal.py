"""
Modal dialog untuk melihat preview hasil komposit foto portrait dan landscape.
"""

from pathlib import Path
from typing import Optional
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw

from src.config.models import SingleBatchConfig, SlotCoordinates
from src.core.validator import load_frame_image, load_photo_image
from src.core.compositor import compose_frame_with_photo
from src.core.exif_handler import normalize_exif_orientation
from src.pipeline.scanner import scan_folder_photos


class CompositePreviewModal(ctk.CTkToplevel):
    """
    Jendela modal untuk meninjau hasil komposit foto dengan frame PNG
    dalam orientasi Portrait dan Landscape sebelum batch diproses.
    """

    def __init__(self, parent, batch_config: SingleBatchConfig):
        super().__init__(parent)
        self.title(f"Preview Hasil Komposit - {batch_config.name}")
        self.geometry("900x700")
        self.minsize(750, 550)

        self.batch_config = batch_config
        self.current_orientation = "portrait"  # "portrait" atau "landscape"
        self._photo_cache: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self.after(50, self._render_preview)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header dan kontrol orientasi
        top_bar = ctk.CTkFrame(self)
        top_bar.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")

        lbl_title = ctk.CTkLabel(
            top_bar,
            text=f"Simulasi Hasil Akhir ({self.batch_config.name})",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_title.pack(side="left", padx=15, pady=10)

        self.seg_btn = ctk.CTkSegmentedButton(
            top_bar,
            values=["Sampel Portrait", "Sampel Landscape"],
            command=self._on_orientation_changed
        )
        self.seg_btn.set("Sampel Portrait")
        self.seg_btn.pack(side="right", padx=15, pady=10)

        # Panel Tampilan Gambar
        self.preview_canvas = ctk.CTkLabel(self, text="Memuat preview...", fg_color="#1A1A1A")
        self.preview_canvas.grid(row=1, column=0, padx=15, pady=10, sticky="nsew")

        # Footer Info
        footer = ctk.CTkFrame(self)
        footer.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="ew")

        slot = self.batch_config.slot_coordinates
        slot_text = f"Slot: X={slot.x}, Y={slot.y}, W={slot.width}, H={slot.height} px" if slot else "Slot: Default"
        self.lbl_info = ctk.CTkLabel(
            footer,
            text=f"Frame: {self.batch_config.frame_path.name if self.batch_config.frame_path else '-'} | {slot_text}",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_info.pack(side="left", padx=15, pady=8)

        btn_close = ctk.CTkButton(footer, text="Tutup", width=90, command=self.destroy)
        btn_close.pack(side="right", padx=15, pady=8)

    def _on_orientation_changed(self, value: str) -> None:
        if "Portrait" in value:
            self.current_orientation = "portrait"
        else:
            self.current_orientation = "landscape"
        self._render_preview()

    def _generate_sample_photo(self) -> Image.Image:
        """Mengambil foto asli dari folder atau menghasilkan foto sintetis."""
        # Cari foto dari folder sumber jika tersedia
        if self.batch_config.input_folder and self.batch_config.input_folder.is_dir():
            files = scan_folder_photos(self.batch_config.input_folder, max_photos=10)
            for f in files:
                try:
                    raw = load_photo_image(f)
                    norm = normalize_exif_orientation(raw)
                    w, h = norm.size
                    if self.current_orientation == "portrait" and h >= w:
                        return norm
                    elif self.current_orientation == "landscape" and w > h:
                        return norm
                except Exception:
                    continue

        # Fallback dummy
        if self.current_orientation == "portrait":
            dummy = Image.new("RGB", (900, 1350), (30, 110, 190))
            d = ImageDraw.Draw(dummy)
            d.text((150, 400), "SAMPLE PORTRAIT PHOTO", fill=(255, 255, 255))
            return dummy
        else:
            dummy = Image.new("RGB", (1400, 900), (40, 160, 90))
            d = ImageDraw.Draw(dummy)
            d.text((250, 300), "SAMPLE LANDSCAPE PHOTO", fill=(255, 255, 255))
            return dummy

    def _render_preview(self) -> None:
        if not self.batch_config.frame_path or not self.batch_config.frame_path.exists():
            self.preview_canvas.configure(text="Frame PNG belum dipilih!")
            return

        slot = self.batch_config.slot_coordinates
        if not slot:
            self.preview_canvas.configure(text="Slot Coordinates belum diatur!")
            return

        try:
            frame_img = load_frame_image(self.batch_config.frame_path)
            photo_img = self._generate_sample_photo()

            # Lakukan alpha compositing murni
            composite = compose_frame_with_photo(frame_img, photo_img, slot)

            # Hitung thumbnail fit ke ukuran canvas preview
            cw = max(200, self.preview_canvas.winfo_width() - 40)
            ch = max(200, self.preview_canvas.winfo_height() - 40)
            scale = min(cw / composite.width, ch / composite.height)
            dw = max(1, int(round(composite.width * scale)))
            dh = max(1, int(round(composite.height * scale)))

            resized_comp = composite.resize((dw, dh), Image.Resampling.BILINEAR)

            # Gunakan CTkImage untuk kualitas rendering yang tajam dan simpan cache referensi
            self._photo_cache = ctk.CTkImage(light_image=resized_comp, dark_image=resized_comp, size=(dw, dh))
            self.preview_canvas.configure(image=self._photo_cache, text="")
        except Exception as exc:
            self.preview_canvas.configure(text=f"Gagal merender preview: {exc}")
