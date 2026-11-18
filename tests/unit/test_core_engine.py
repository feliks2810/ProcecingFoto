"""
Unit test suite untuk Core Image Processing Engine PhotoFrameProcessor.
"""

from pathlib import Path
import pytest
from PIL import Image
import numpy as np

from src.config.models import SlotCoordinates
from src.core.validator import (
    validate_photo_path,
    validate_frame_path,
    load_photo_image,
    load_frame_image,
    ImageValidationError,
)
from src.core.exif_handler import normalize_exif_orientation, get_exif_orientation
from src.core.transform import resize_and_center_crop
from src.core.compositor import compose_frame_with_photo, SlotOutOfBoundsError
from src.core.writer import get_unique_filepath, save_image_safely
from src.core.processor import process_single_photo
from tests.conftest import compute_sha256


class TestValidationAndLoading:
    """Pengujian modul validasi dan pembacaan citra."""

    def test_validate_nonexistent_photo_raises_error(self, tmp_path: Path):
        fake_path = tmp_path / "tidak_ada.jpg"
        with pytest.raises(FileNotFoundError):
            validate_photo_path(fake_path)

    def test_validate_corrupted_zero_byte_photo(self, tmp_path: Path):
        zero_byte = tmp_path / "corrupt.jpg"
        zero_byte.write_bytes(b"")
        with pytest.raises(ImageValidationError, match="kosong"):
            validate_photo_path(zero_byte)

    def test_validate_unsupported_extension(self, tmp_path: Path):
        bad_ext = tmp_path / "doc.pdf"
        bad_ext.write_text("dummy text")
        with pytest.raises(ImageValidationError, match="tidak didukung"):
            validate_photo_path(bad_ext)

    def test_validate_frame_must_be_png(self, tmp_path: Path):
        jpg_frame = tmp_path / "frame.jpg"
        jpg_frame.write_bytes(b"content")
        with pytest.raises(ImageValidationError, match="berformat PNG"):
            validate_frame_path(jpg_frame)

    def test_load_frame_ensures_rgba_mode(self, sample_frame_png: Path):
        frame = load_frame_image(sample_frame_png)
        assert frame.mode == "RGBA"
        assert frame.size == (1000, 1000)


class TestExifOrientation:
    """Pengujian koreksi rotasi fisik berbasis metadata EXIF."""

    def test_exif_tag_detected(self, sample_exif_photo: Path):
        with Image.open(sample_exif_photo) as img:
            tag = get_exif_orientation(img)
            assert tag == 6

    def test_normalize_exif_transposes_dimensions(self, sample_exif_photo: Path):
        with Image.open(sample_exif_photo) as raw_img:
            assert raw_img.size == (1200, 800)  # Landscape fisik sebelum transpose
            corrected = normalize_exif_orientation(raw_img)
            # Tag 6 memutar 90 derajat searah jarum jam: (1200, 800) -> (800, 1200) tegak
            assert corrected.size == (800, 1200)


class TestTransformAspectCrop:
    """Pengujian penyesuaian rasio aspek, resize, dan center-crop."""

    def test_portrait_photo_to_square_slot(self, sample_portrait_photo: Path):
        with Image.open(sample_portrait_photo) as photo:
            assert photo.size == (800, 1200)  # Portrait
            # Crop ke slot persegi 400x400
            result = resize_and_center_crop(photo, (400, 400))
            assert result.size == (400, 400)

    def test_landscape_photo_to_portrait_slot(self, sample_landscape_photo: Path):
        with Image.open(sample_landscape_photo) as photo:
            assert photo.size == (1600, 900)  # Landscape
            # Crop ke slot portrait 300x500
            result = resize_and_center_crop(photo, (300, 500))
            assert result.size == (300, 500)

    def test_invalid_target_size_raises_value_error(self, sample_portrait_photo: Path):
        with Image.open(sample_portrait_photo) as photo:
            with pytest.raises(ValueError):
                resize_and_center_crop(photo, (0, 500))
            with pytest.raises(ValueError):
                resize_and_center_crop(photo, (-100, 200))


class TestCompositingAndLayering:
    """Pengujian penggabungan citra, layering, dan validasi slot koordinat."""

    def test_slot_out_of_bounds_raises_error(self, sample_frame_png: Path, sample_portrait_photo: Path):
        frame = load_frame_image(sample_frame_png)
        photo = load_photo_image(sample_portrait_photo)

        # Slot melewati batas kanvas frame 1000x1000: x=800 + width=300 = 1100 > 1000
        invalid_slot = SlotCoordinates(x=800, y=200, width=300, height=400)
        with pytest.raises(SlotOutOfBoundsError, match="melampaui lebar frame"):
            compose_frame_with_photo(frame, photo, invalid_slot)

    def test_composite_dimensions_and_pixel_integrity(self, sample_frame_png: Path, sample_portrait_photo: Path):
        frame = load_frame_image(sample_frame_png)
        photo = load_photo_image(sample_portrait_photo)  # Foto berwarna biru (0, 100, 255)

        # Slot di area lubang transparan frame: (200, 200, 600, 600)
        slot = SlotCoordinates(x=200, y=200, width=600, height=600)
        composite = compose_frame_with_photo(frame, photo, slot)

        # 1. Dimensi harus persis sama dengan frame
        assert composite.size == (1000, 1000)
        assert composite.mode == "RGBA"

        arr = np.array(composite)

        # 2. Sudut (50, 50) adalah ornamen frame merah: RGBA [255, 0, 0, 255]
        corner_pixel = arr[50, 50]
        assert corner_pixel[0] > 200, "Piksel merah ornamen frame harus tampak di lapisan teratas"
        assert corner_pixel[2] < 50, "Piksel biru tidak boleh menembus ornamen frame"

        # 3. Titik tengah (500, 500) adalah lubang foto: Foto biru harus tampak
        center_pixel = arr[500, 500]
        assert center_pixel[2] > 200, "Piksel foto biru pengguna harus tampak di dalam lubang slot"
        assert center_pixel[3] == 255, "Alpha area foto harus opaque penuh (255)"


class TestWriterAndNonDestructiveSafety:
    """Pengujian penyimpanan aman, pencegahan penimpaan file, dan keutuhan file asli."""

    def test_output_does_not_overwrite_existing_file(self, tmp_path: Path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        existing_file = out_dir / "foto_framed.png"
        existing_file.write_text("initial content")

        dummy_img = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        saved_path = save_image_safely(
            image=dummy_img,
            output_path=existing_file,
            allow_overwrite=False
        )

        # File baru harus diberi nama unik, bukan menimpa
        assert saved_path != existing_file
        assert saved_path.name == "foto_framed_1.png"
        assert saved_path.exists()

        # File awal harus tetap utuh isinya
        assert existing_file.read_text() == "initial content"


class TestSinglePhotoProcessorIntegration:
    """Pengujian end-to-end fungsi process_single_photo."""

    def test_process_portrait_photo_success(
        self,
        sample_portrait_photo: Path,
        sample_frame_png: Path,
        tmp_path: Path
    ):
        out_dir = tmp_path / "out"
        slot = SlotCoordinates(x=200, y=200, width=600, height=600)
        initial_hash = compute_sha256(sample_portrait_photo)

        result = process_single_photo(
            photo_path=sample_portrait_photo,
            frame_path=sample_frame_png,
            slot=slot,
            output_dir=out_dir
        )

        assert result.success is True
        assert result.output_file is not None
        assert result.output_file.exists()
        assert result.execution_time_ms > 0

        # Verifikasi non-destructive: Hash foto sumber tidak boleh berubah
        post_hash = compute_sha256(sample_portrait_photo)
        assert post_hash == initial_hash, "File foto sumber termodifikasi secara tidak sengaja!"

    def test_process_landscape_photo_success(
        self,
        sample_landscape_photo: Path,
        sample_frame_png: Path,
        tmp_path: Path
    ):
        out_dir = tmp_path / "out"
        slot = SlotCoordinates(x=200, y=200, width=600, height=600)

        result = process_single_photo(
            photo_path=sample_landscape_photo,
            frame_path=sample_frame_png,
            slot=slot,
            output_dir=out_dir
        )

        assert result.success is True
        assert result.output_file.exists()

    def test_process_photo_with_exif_orientation_success(
        self,
        sample_exif_photo: Path,
        sample_frame_png: Path,
        tmp_path: Path
    ):
        out_dir = tmp_path / "out"
        slot = SlotCoordinates(x=200, y=200, width=600, height=600)

        result = process_single_photo(
            photo_path=sample_exif_photo,
            frame_path=sample_frame_png,
            slot=slot,
            output_dir=out_dir
        )

        assert result.success is True
        assert result.output_file.exists()

    def test_process_nonexistent_photo_fails_gracefully(
        self,
        sample_frame_png: Path,
        tmp_path: Path
    ):
        fake_photo = tmp_path / "ghost.jpg"
        slot = SlotCoordinates(x=200, y=200, width=600, height=600)

        result = process_single_photo(
            photo_path=fake_photo,
            frame_path=sample_frame_png,
            slot=slot,
            output_dir=tmp_path / "out"
        )

        assert result.success is False
        assert result.output_file is None
        assert "tidak ditemukan" in result.error_message

    def test_process_corrupt_file_fails_gracefully(
        self,
        sample_frame_png: Path,
        tmp_path: Path
    ):
        corrupt_photo = tmp_path / "corrupt.jpg"
        corrupt_photo.write_text("ini bukan foto jpg valid")
        slot = SlotCoordinates(x=200, y=200, width=600, height=600)

        result = process_single_photo(
            photo_path=corrupt_photo,
            frame_path=sample_frame_png,
            slot=slot,
            output_dir=tmp_path / "out"
        )

        assert result.success is False
        assert result.output_file is None
        assert "Gagal membaca" in result.error_message
