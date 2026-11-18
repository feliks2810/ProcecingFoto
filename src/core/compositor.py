"""
Modul compositing citra: penggabungan underlay foto dan overlay frame PNG transparan.
"""

from typing import Union
from PIL import Image

from src.config.models import SlotCoordinates
from src.core.transform import resize_and_center_crop


class SlotOutOfBoundsError(ValueError):
    """Pengecualian ketika koordinat slot melebihi batas kanvas frame."""
    pass


def validate_slot_within_frame(slot: SlotCoordinates, frame_size: tuple[int, int]) -> None:
    """
    Memvalidasi bahwa batas SlotCoordinates berada sepenuhnya di dalam dimensi frame.
    """
    frame_w, frame_h = frame_size

    if slot.x < 0 or slot.y < 0:
        raise SlotOutOfBoundsError(f"Koordinat slot negatif: x={slot.x}, y={slot.y}")

    if slot.width <= 0 or slot.height <= 0:
        raise SlotOutOfBoundsError(f"Dimensi slot harus positif: width={slot.width}, height={slot.height}")

    if slot.x + slot.width > frame_w:
        raise SlotOutOfBoundsError(
            f"Batas kanan slot ({slot.x + slot.width}px) melampaui lebar frame ({frame_w}px)."
        )

    if slot.y + slot.height > frame_h:
        raise SlotOutOfBoundsError(
            f"Batas bawah slot ({slot.y + slot.height}px) melampaui tinggi frame ({frame_h}px)."
        )


def compose_frame_with_photo(
    frame: Image.Image,
    photo: Image.Image,
    slot: SlotCoordinates
) -> Image.Image:
    """
    Menggabungkan foto dengan template frame PNG transparan menggunakan alpha compositing.

    Prinsip Layering:
    - Kanvas dasar (transparan seukuran frame).
    - Lapisan foto di bawah (underlay), ditempatkan tepat di (slot.x, slot.y) setelah
      di-crop & resize sesuai (slot.width, slot.height).
    - Lapisan frame PNG di atas (overlay / topmost layer), sehingga ornamen frame menutupi
      tepian foto, dan foto terlihat melalui area transparan frame.

    :param frame: Citra frame PNG (harus mode RGBA).
    :param photo: Citra foto pengguna (RGB atau RGBA).
    :param slot: Model SlotCoordinates target peletakan foto.
    :return: Objek Image baru dalam mode RGBA dengan dimensi persis seukuran frame.
    """
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")

    # Validasi koordinat slot terhadap kanvas frame
    validate_slot_within_frame(slot, frame.size)

    # Pastikan foto dalam mode RGBA untuk alpha compositing yang konsisten
    photo_rgba = photo.convert("RGBA") if photo.mode != "RGBA" else photo

    # 1. Transformasi foto agar proporsional mengisi slot target
    processed_photo = resize_and_center_crop(photo_rgba, (slot.width, slot.height))

    # 2. Buat kanvas dasar transparan dengan ukuran persis sama dengan frame
    base_canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))

    # 3. Tempel foto tepat di koordinat slot yang ditentukan
    base_canvas.paste(processed_photo, (slot.x, slot.y))

    # 4. Tumpuk frame transparan di lapisan teratas (alpha compositing)
    # Piksel ornamen frame (alpha 255) akan menutup foto, sedangkan piksel lubang (alpha 0)
    # akan menampakkan foto di bawahnya secara utuh.
    final_composite = Image.alpha_composite(base_canvas, frame)

    return final_composite
