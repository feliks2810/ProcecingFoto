"""
Modul Interactive Photo Placement Editor untuk PhotoFrameProcessor.
Menyediakan kanvas visual untuk mengatur SlotCoordinates (posisi dan ukuran foto pada frame PNG).
"""

from pathlib import Path
from typing import Callable, Optional, Tuple
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw

from src.config.models import SlotCoordinates
from src.core.validator import load_frame_image, load_photo_image
from src.core.transform import resize_and_center_crop
from src.core.exif_handler import normalize_exif_orientation
from src.core.hole_detector import detect_transparent_hole


class CanvasCoordinateTransformer:
    """
    Kelas murni untuk kalkulasi transformasi koordinat kanvas ke resolusi asli citra PNG.
    Memungkinkan pengujian unit matematis tanpa memerlukan display GUI aktif.
    """

    def __init__(self, frame_size: Tuple[int, int], canvas_size: Tuple[int, int]):
        self.frame_w, self.frame_h = frame_size
        self.canvas_w, self.canvas_h = canvas_size

        if self.frame_w <= 0 or self.frame_h <= 0 or self.canvas_w <= 0 or self.canvas_h <= 0:
            self.scale = 1.0
            self.offset_x = 0.0
            self.offset_y = 0.0
            self.display_w = self.frame_w
            self.display_h = self.frame_h
            return

        # Skala aspect-fit agar frame tampil utuh di kanvas
        scale_x = self.canvas_w / self.frame_w
        scale_y = self.canvas_h / self.frame_h
        self.scale = min(scale_x, scale_y)

        self.display_w = int(round(self.frame_w * self.scale))
        self.display_h = int(round(self.frame_h * self.scale))

        # Posisi tengah kanvas
        self.offset_x = (self.canvas_w - self.display_w) / 2.0
        self.offset_y = (self.canvas_h - self.display_h) / 2.0

    def canvas_to_image_coords(self, cx: float, cy: float) -> Tuple[int, int]:
        """Mengonversi titik piksel kanvas ke koordinat piksel asli citra PNG."""
        if self.scale <= 0:
            return (0, 0)
        rel_x = cx - self.offset_x
        rel_y = cy - self.offset_y

        img_x = int(round(rel_x / self.scale))
        img_y = int(round(rel_y / self.scale))

        # Batasi ke batas fisik citra
        img_x = max(0, min(self.frame_w, img_x))
        img_y = max(0, min(self.frame_h, img_y))
        return (img_x, img_y)

    def image_to_canvas_coords(self, ix: float, iy: float) -> Tuple[float, float]:
        """Mengonversi titik piksel asli citra PNG ke titik koordinat kanvas."""
        cx = (ix * self.scale) + self.offset_x
        cy = (iy * self.scale) + self.offset_y
        return (cx, cy)

    def slot_to_canvas_box(self, slot: SlotCoordinates) -> Tuple[float, float, float, float]:
        """Mengonversi SlotCoordinates asli ke bounding box kanvas (x1, y1, x2, y2)."""
        x1, y1 = self.image_to_canvas_coords(slot.x, slot.y)
        x2, y2 = self.image_to_canvas_coords(slot.x + slot.width, slot.y + slot.height)
        return (x1, y1, x2, y2)

    def canvas_box_to_slot(self, c_x1: float, c_y1: float, c_x2: float, c_y2: float) -> SlotCoordinates:
        """Mengonversi bounding box kanvas ke SlotCoordinates asli citra PNG."""
        x1, y1 = self.canvas_to_image_coords(min(c_x1, c_x2), min(c_y1, c_y2))
        x2, y2 = self.canvas_to_image_coords(max(c_x1, c_x2), max(c_y1, c_y2))

        width = max(10, x2 - x1)
        height = max(10, y2 - y1)

        # Pastikan tidak melewati batas lebar/tinggi asli frame
        if x1 + width > self.frame_w:
            width = max(10, self.frame_w - x1)
        if y1 + height > self.frame_h:
            height = max(10, self.frame_h - y1)

        return SlotCoordinates(x=x1, y=y1, width=width, height=height)


class PhotoPlacementEditor(ctk.CTkToplevel):
    """
    Jendela interaktif Photo Placement Editor:
    - Menampilkan frame PNG transparan.
    - Drag mouse untuk membuat/menggeser area slot foto.
    - Input numerik presisi (X, Y, Lebar, Tinggi).
    - Tombol deteksi otomatis lubang transparan.
    - Preview foto sampel di balik frame.
    - Menyimpan konfigurasi koordinat.
    """

    def __init__(
        self,
        parent,
        frame_path: Path,
        initial_slot: Optional[SlotCoordinates] = None,
        sample_photo_path: Optional[Path] = None,
        on_save_slot: Optional[Callable[[SlotCoordinates], None]] = None
    ):
        super().__init__(parent)
        self.title("Interactive Photo Placement Editor")
        self.geometry("1100x750")
        self.minsize(900, 600)

        self.frame_path = frame_path
        self.sample_photo_path = sample_photo_path
        self.on_save_slot = on_save_slot

        # Load frame asli
        self.original_frame = load_frame_image(self.frame_path)
        self.frame_w, self.frame_h = self.original_frame.size

        # Slot koordinat aktif (jika belum ada, default 70% di tengah)
        if initial_slot:
            self.current_slot = initial_slot
        else:
            w = int(self.frame_w * 0.7)
            h = int(self.frame_h * 0.7)
            x = (self.frame_w - w) // 2
            y = (self.frame_h - h) // 2
            self.current_slot = SlotCoordinates(x=x, y=y, width=w, height=h)

        # Sample photo internal
        self.sample_photo = self._load_sample_photo()

        # State interaksi kanvas
        self.transformer = CanvasCoordinateTransformer((self.frame_w, self.frame_h), (600, 600))
        self.drag_mode: Optional[str] = None  # "draw", "move", "resize"
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.initial_slot_on_drag: Optional[SlotCoordinates] = None

        # Cache citra kanvas
        self._canvas_bg_photo: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self.after(100, self._initial_render)

    def _load_sample_photo(self) -> Image.Image:
        """Memuat sampel foto dari path atau membuat foto sintetis dummy."""
        if self.sample_photo_path and self.sample_photo_path.exists():
            try:
                raw = load_photo_image(self.sample_photo_path)
                return normalize_exif_orientation(raw)
            except Exception:
                pass
        # Buat foto dummy portrait default
        dummy = Image.new("RGB", (800, 1200), (45, 120, 210))
        d = ImageDraw.Draw(dummy)
        d.text((100, 200), "SAMPLE PHOTO", fill=(255, 255, 255))
        return dummy

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Panel Kiri: Kanvas Interaktif
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#202020", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        # 2. Panel Kanan: Kontrol & Input Numerik
        self.ctrl_panel = ctk.CTkFrame(self, width=320)
        self.ctrl_panel.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")
        self.ctrl_panel.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self.ctrl_panel,
            text="Pengaturan Slot Foto",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="w")

        info_frame = ctk.CTkLabel(
            self.ctrl_panel,
            text=f"Ukuran Frame: {self.frame_w} x {self.frame_h} px",
            font=ctk.CTkFont(size=12)
        )
        info_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="w")

        # Input Koordinat Numerik
        labels = [("X (Kiri)", "entry_x"), ("Y (Atas)", "entry_y"), ("Lebar (W)", "entry_w"), ("Tinggi (H)", "entry_h")]
        self.entries = {}
        for idx, (lbl_text, attr_name) in enumerate(labels, start=2):
            lbl = ctk.CTkLabel(self.ctrl_panel, text=lbl_text, anchor="w")
            lbl.grid(row=idx, column=0, padx=15, pady=6, sticky="w")
            ent = ctk.CTkEntry(self.ctrl_panel, width=110)
            ent.grid(row=idx, column=1, padx=15, pady=6, sticky="ew")
            self.entries[attr_name] = ent

        btn_apply_numeric = ctk.CTkButton(
            self.ctrl_panel,
            text="Terapkan Koordinat",
            command=self._on_apply_numeric
        )
        btn_apply_numeric.grid(row=6, column=0, columnspan=2, padx=15, pady=12, sticky="ew")

        # Tombol Deteksi Otomatis & Ganti Sampel
        btn_auto_detect = ctk.CTkButton(
            self.ctrl_panel,
            text="Deteksi Lubang Otomatis",
            fg_color="#3A7060",
            hover_color="#2A5040",
            command=self._on_auto_detect_hole
        )
        btn_auto_detect.grid(row=7, column=0, columnspan=2, padx=15, pady=6, sticky="ew")

        btn_toggle_sample = ctk.CTkButton(
            self.ctrl_panel,
            text="Ganti Orientasi Sampel (P/L)",
            fg_color="#455A64",
            hover_color="#37474F",
            command=self._toggle_sample_orientation
        )
        btn_toggle_sample.grid(row=8, column=0, columnspan=2, padx=15, pady=6, sticky="ew")

        # Petunjuk Drag
        guide_text = (
            "Petunjuk Penggunaan:\n"
            "• Drag di dalam kotak untuk menggeser.\n"
            "• Drag area luar untuk menggambar area baru.\n"
            "• Atau isi nilai X, Y, W, H lalu klik Terapkan."
        )
        guide_lbl = ctk.CTkLabel(
            self.ctrl_panel,
            text=guide_text,
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color="#B0B0B0"
        )
        guide_lbl.grid(row=9, column=0, columnspan=2, padx=15, pady=15, sticky="w")

        # Tombol Simpan & Tutup
        btn_save = ctk.CTkButton(
            self.ctrl_panel,
            text="Simpan Koordinat",
            fg_color="#1E88E5",
            hover_color="#1565C0",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_save_and_close
        )
        btn_save.grid(row=10, column=0, columnspan=2, padx=15, pady=(20, 10), sticky="ew")

    def _initial_render(self) -> None:
        self._update_numeric_entries()
        self._render_canvas()

    def _update_numeric_entries(self) -> None:
        for attr, val in [
            ("entry_x", self.current_slot.x),
            ("entry_y", self.current_slot.y),
            ("entry_w", self.current_slot.width),
            ("entry_h", self.current_slot.height),
        ]:
            entry = self.entries[attr]
            entry.delete(0, "end")
            entry.insert(0, str(val))

    def _on_apply_numeric(self) -> None:
        try:
            x = int(self.entries["entry_x"].get().strip())
            y = int(self.entries["entry_y"].get().strip())
            w = int(self.entries["entry_w"].get().strip())
            h = int(self.entries["entry_h"].get().strip())
            # Validasi batas
            x = max(0, min(self.frame_w - 10, x))
            y = max(0, min(self.frame_h - 10, y))
            w = max(10, min(self.frame_w - x, w))
            h = max(10, min(self.frame_h - y, h))

            self.current_slot = SlotCoordinates(x=x, y=y, width=w, height=h)
            self._update_numeric_entries()
            self._render_canvas()
        except ValueError:
            pass

    def _on_auto_detect_hole(self) -> None:
        """Mendeteksi bounding box area transparan pada frame."""
        detected = detect_transparent_hole(self.original_frame)
        if detected:
            self.current_slot = detected
            self._update_numeric_entries()
            self._render_canvas()

    def _toggle_sample_orientation(self) -> None:
        """Membalik rasio aspek foto sampel antara portrait dan landscape."""
        w, h = self.sample_photo.size
        self.sample_photo = self.sample_photo.resize((h, w), Image.Resampling.BILINEAR)
        self._render_canvas()

    def _on_canvas_resize(self, event) -> None:
        if event.width > 50 and event.height > 50:
            self.transformer = CanvasCoordinateTransformer(
                (self.frame_w, self.frame_h),
                (event.width, event.height)
            )
            self._render_canvas()

    def _render_canvas(self) -> None:
        """Merender tampilan frame, foto sampel di balik frame, dan bounding box."""
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            return

        self.canvas.delete("all")

        # 1. Buat komposisi visual skala tampilan
        # Kanvas dasar transparan
        vis_base = Image.new("RGBA", (self.frame_w, self.frame_h), (40, 40, 40, 255))

        # Tempel foto sampel di area slot
        photo_cropped = resize_and_center_crop(
            self.sample_photo,
            (self.current_slot.width, self.current_slot.height)
        )
        vis_base.paste(photo_cropped, (self.current_slot.x, self.current_slot.y))

        # Tumpuk frame asli di atasnya
        composite_view = Image.alpha_composite(vis_base, self.original_frame)

        # Resize untuk ditampilkan di kanvas
        disp_w = self.transformer.display_w
        disp_h = self.transformer.display_h
        if disp_w > 0 and disp_h > 0:
            resized_view = composite_view.resize((disp_w, disp_h), Image.Resampling.BILINEAR)
            self._canvas_bg_photo = ImageTk.PhotoImage(resized_view)
            self.canvas.create_image(
                self.transformer.offset_x,
                self.transformer.offset_y,
                anchor="nw",
                image=self._canvas_bg_photo
            )

        # 2. Gambar Bounding Box Slot di atas kanvas
        x1, y1, x2, y2 = self.transformer.slot_to_canvas_box(self.current_slot)
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#00E5FF",
            width=2,
            dash=(6, 4),
            tags="slot_box"
        )

        # Gambar handle sudut
        hs = 4
        for hx, hy in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
            self.canvas.create_rectangle(
                hx - hs, hy - hs, hx + hs, hy + hs,
                fill="#00E5FF",
                outline="#FFFFFF",
                tags="handle"
            )

    def _on_mouse_down(self, event) -> None:
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.initial_slot_on_drag = self.current_slot

        # Periksa apakah klik berada di dalam slot box yang ada
        x1, y1, x2, y2 = self.transformer.slot_to_canvas_box(self.current_slot)
        if x1 <= event.x <= x2 and y1 <= event.y <= y2:
            self.drag_mode = "move"
        else:
            self.drag_mode = "draw"

    def _on_mouse_drag(self, event) -> None:
        if not self.drag_mode or not self.initial_slot_on_drag:
            return

        if self.drag_mode == "move":
            # Hitung delta geser
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y

            delta_img_x = int(round(dx / self.transformer.scale)) if self.transformer.scale > 0 else 0
            delta_img_y = int(round(dy / self.transformer.scale)) if self.transformer.scale > 0 else 0

            new_x = max(0, min(self.frame_w - self.initial_slot_on_drag.width, self.initial_slot_on_drag.x + delta_img_x))
            new_y = max(0, min(self.frame_h - self.initial_slot_on_drag.height, self.initial_slot_on_drag.y + delta_img_y))

            self.current_slot = SlotCoordinates(
                x=new_x,
                y=new_y,
                width=self.initial_slot_on_drag.width,
                height=self.initial_slot_on_drag.height
            )
            self._update_numeric_entries()
            self._render_canvas()

        elif self.drag_mode == "draw":
            # Gambar kotak baru dari drag_start ke posisi sekarang
            new_slot = self.transformer.canvas_box_to_slot(
                self.drag_start_x,
                self.drag_start_y,
                event.x,
                event.y
            )
            self.current_slot = new_slot
            self._update_numeric_entries()
            self._render_canvas()

    def _on_mouse_up(self, event) -> None:
        self.drag_mode = None
        self.initial_slot_on_drag = None
        self._update_numeric_entries()
        self._render_canvas()

    def _on_save_and_close(self) -> None:
        if self.on_save_slot:
            self.on_save_slot(self.current_slot)
        self.destroy()
