"""
Pytest configuration and synthetic fixtures for PhotoFrameProcessor.
"""

import hashlib
from pathlib import Path
from typing import Tuple
import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def sample_frame_png(tmp_path: Path) -> Path:
    """
    Membuat frame PNG transparan berukuran 1000x1000 piksel:
    - Area ornamen bingkai (tepi): Merah solid (RGBA: 255, 0, 0, 255)
    - Area slot tengah (lubang foto): Transparan penuh (RGBA: 0, 0, 0, 0)
      Koordinat lubang: x=200, y=200, width=600, height=600.
    """
    frame_path = tmp_path / "test_frame.png"
    # Kanvas merah solid
    img = Image.new("RGBA", (1000, 1000), (255, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    # Potong lubang transparan di tengah
    draw.rectangle([200, 200, 800, 800], fill=(0, 0, 0, 0))
    img.save(frame_path, "PNG")
    return frame_path


@pytest.fixture
def sample_portrait_photo(tmp_path: Path) -> Path:
    """
    Membuat file foto portrait dummy (800x1200 piksel) berwarna biru.
    """
    photo_path = tmp_path / "portrait_photo.jpg"
    img = Image.new("RGB", (800, 1200), (0, 100, 255))
    img.save(photo_path, "JPEG", quality=95)
    return photo_path


@pytest.fixture
def sample_landscape_photo(tmp_path: Path) -> Path:
    """
    Membuat file foto landscape dummy (1600x900 piksel) berwarna hijau.
    """
    photo_path = tmp_path / "landscape_photo.jpg"
    img = Image.new("RGB", (1600, 900), (0, 200, 100))
    img.save(photo_path, "JPEG", quality=95)
    return photo_path


@pytest.fixture
def sample_exif_photo(tmp_path: Path) -> Path:
    """
    Membuat foto landscape fisik (1200x800) tetapi memiliki EXIF tag 6
    (Orientation = Rotated 90 CW, sehingga aslinya harus tegak/portrait).
    """
    photo_path = tmp_path / "exif_photo.jpg"
    img = Image.new("RGB", (1200, 800), (200, 50, 150))
    exif = img.getexif()
    exif[0x0112] = 6  # 6 = Rotate 90 CW
    img.save(photo_path, "JPEG", exif=exif, quality=95)
    return photo_path


def compute_sha256(filepath: Path) -> str:
    """Menghitung hash SHA-256 dari file untuk membuktikan integritas non-destructive."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()
