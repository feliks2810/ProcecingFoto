"""
Unit test suite untuk GUI Components, Canvas Coordinate Transformer, dan Controller.
"""

import time
import threading
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from PIL import Image

from src.config.models import BatchConfig, SingleBatchConfig, SlotCoordinates
from src.config.persistence import save_user_config, load_user_config
from src.gui.app import resolve_default_frame
from src.gui.components.placement_editor import CanvasCoordinateTransformer
from src.gui.controllers.main_controller import MainAppController


class TestCanvasCoordinateTransformer:
    """Pengujian matematika transformasi koordinat kanvas visual ke resolusi asli citra PNG."""

    def test_square_frame_uniform_scaling(self):
        # Frame asli 1000x1000 pada kanvas 500x500 (Skala 0.5)
        transformer = CanvasCoordinateTransformer(frame_size=(1000, 1000), canvas_size=(500, 500))

        assert transformer.scale == 0.5
        assert transformer.offset_x == 0.0
        assert transformer.offset_y == 0.0

        # Titik tengah kanvas (250, 250) harus memetakan ke titik tengah asli citra (500, 500)
        img_pt = transformer.canvas_to_image_coords(250, 250)
        assert img_pt == (500, 500)

        # Sebaliknya, citra (500, 500) harus memetakan ke kanvas (250, 250)
        canv_pt = transformer.image_to_canvas_coords(500, 500)
        assert canv_pt == (250.0, 250.0)

    def test_aspect_fit_letterboxing(self):
        # Frame landscape 1200x600 (rasio 2:1) pada kanvas persegi 600x600
        transformer = CanvasCoordinateTransformer(frame_size=(1200, 600), canvas_size=(600, 600))

        # Skala harus dibatasi oleh lebar: 600 / 1200 = 0.5
        assert transformer.scale == 0.5
        assert transformer.display_w == 600
        assert transformer.display_h == 300
        assert transformer.offset_x == 0.0
        # Offset vertikal (600 - 300) / 2 = 150
        assert transformer.offset_y == 150.0

        # Titik paling atas frame (y=0 asli) berada pada y=150 di kanvas
        assert transformer.image_to_canvas_coords(0, 0) == (0.0, 150.0)
        assert transformer.canvas_to_image_coords(0, 150) == (0, 0)

    def test_slot_roundtrip_conversion(self):
        # Frame 1920x1080 pada kanvas 800x600
        transformer = CanvasCoordinateTransformer(frame_size=(1920, 1080), canvas_size=(800, 600))

        original_slot = SlotCoordinates(x=250, y=180, width=850, height=620)

        # Konversi ke kanvas lalu kembalikan ke slot asli
        c_x1, c_y1, c_x2, c_y2 = transformer.slot_to_canvas_box(original_slot)
        reconstructed_slot = transformer.canvas_box_to_slot(c_x1, c_y1, c_x2, c_y2)

        # Toleransi pembulatan sub-piksel maksimal 1-2 piksel
        assert abs(reconstructed_slot.x - original_slot.x) <= 2
        assert abs(reconstructed_slot.y - original_slot.y) <= 2
        assert abs(reconstructed_slot.width - original_slot.width) <= 2
        assert abs(reconstructed_slot.height - original_slot.height) <= 2

    def test_canvas_box_clamped_to_image_boundaries(self):
        transformer = CanvasCoordinateTransformer(frame_size=(1000, 1000), canvas_size=(500, 500))

        # User menarik mouse keluar dari batas kanvas (misal -50 sampai 600)
        clamped_slot = transformer.canvas_box_to_slot(-50, -50, 600, 600)
        assert clamped_slot.x >= 0
        assert clamped_slot.y >= 0
        assert clamped_slot.x + clamped_slot.width <= 1000
        assert clamped_slot.y + clamped_slot.height <= 1000


class TestConfigPersistenceAndValidation:
    """Pengujian penyimpanan, pemuatan, dan validasi konfigurasi batch."""

    def test_batch_config_serialization_and_deserialization(self, tmp_path: Path):
        slot = SlotCoordinates(x=100, y=150, width=500, height=600)
        cfg = BatchConfig(
            output_folder=tmp_path / "out",
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Satu",
                input_folder=tmp_path / "in1",
                frame_path=tmp_path / "frame1.png",
                slot_coordinates=slot,
                max_photos=250
            ),
            batch_2=SingleBatchConfig(
                batch_id="batch_2",
                name="Batch Dua",
                max_photos=250
            )
        )

        data = cfg.model_dump()
        restored = BatchConfig.model_validate(data)

        assert restored.batch_1.slot_coordinates.to_tuple() == (100, 150, 500, 600)
        assert restored.batch_1.name == "Batch Satu"
        assert restored.output_folder == tmp_path / "out"

    def test_save_and_load_user_config_file(self, tmp_path: Path):
        cfg_file = tmp_path / "custom_config.json"
        cfg = BatchConfig(
            output_folder=tmp_path / "saved_out",
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Simpan",
                slot_coordinates=SlotCoordinates(x=20, y=30, width=400, height=500)
            )
        )

        # Simpan
        assert save_user_config(cfg, cfg_file) is True
        assert cfg_file.exists()

        # Muat kembali
        loaded = load_user_config(cfg_file)
        assert loaded is not None
        assert loaded.output_folder == tmp_path / "saved_out"
        assert loaded.batch_1.slot_coordinates.x == 20

    def test_load_corrupted_config_returns_none(self, tmp_path: Path):
        bad_file = tmp_path / "bad_config.json"
        bad_file.write_text("{ json rusak / tidak valid }", encoding="utf-8")
        assert load_user_config(bad_file) is None

    def test_load_nonexistent_config_returns_none(self, tmp_path: Path):
        ghost_file = tmp_path / "tidak_ada.json"
        assert load_user_config(ghost_file) is None


class DummyRoot:
    """Mock root untuk mensimulasikan root.after() Tkinter tanpa dependensi window server."""
    def __init__(self):
        self.dispatched_tasks = []

    def after(self, ms, func, *args):
        # Simpan atau jalankan langsung
        func(*args)


class TestMainAppController:
    """Pengujian logika controller, background threading, dan pembatalan."""

    def test_controller_validation_missing_folders(self, tmp_path: Path):
        root = DummyRoot()
        cfg = BatchConfig(output_folder=tmp_path / "out")
        ctrl = MainAppController(root=root, config=cfg)

        is_valid, msg = ctrl.validate_configuration()
        assert is_valid is False
        assert "folder foto dan frame PNG" in msg

    def test_controller_threading_progress_and_completion(self, tmp_path: Path, monkeypatch):
        # Mock messagebox agar tidak memblokir test execution
        monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: None)
        monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg: None)

        root = DummyRoot()
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        out_dir = tmp_path / "out"

        # Siapkan 2 foto dan 1 frame
        frame_p = tmp_path / "f.png"
        Image.new("RGBA", (400, 400), (255, 0, 0, 255)).save(frame_p, "PNG")

        Image.new("RGB", (200, 200), (1, 1, 1)).save(in_dir / "p1.jpg", "JPEG")
        Image.new("RGB", (200, 200), (2, 2, 2)).save(in_dir / "p2.jpg", "JPEG")

        cfg = BatchConfig(
            output_folder=out_dir,
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="B1",
                input_folder=in_dir,
                frame_path=frame_p,
                slot_coordinates=SlotCoordinates(x=50, y=50, width=300, height=300)
            )
        )

        progress_events = []
        logs = []
        state_changes = []

        ctrl = MainAppController(
            root=root,
            config=cfg,
            on_progress_ui=lambda c, t, s, f, fn, eta: progress_events.append((c, t, s)),
            on_log_ui=lambda m: logs.append(m),
            on_state_change=lambda is_busy: state_changes.append(is_busy)
        )

        is_valid, _ = ctrl.validate_configuration()
        assert is_valid is True

        # Jalankan worker secara sinkron dalam test dengan memanggil worker langsung
        ctrl._run_pipeline_worker()

        # Verifikasi event progress terpanggil
        assert len(progress_events) == 2
        assert progress_events[-1] == (2, 2, 2)
        assert any("MEMULAI" in m or "Laporan disimpan" in m for m in logs)

    def test_controller_cancellation(self, tmp_path: Path):
        root = DummyRoot()
        cfg = BatchConfig(output_folder=tmp_path / "out")
        ctrl = MainAppController(root=root, config=cfg)

        ctrl._is_running = True
        ctrl.cancel_processing()
        assert ctrl._cancel_event.is_set() is True


class TestFrameResolutionHierarchy:
    """Pengujian resolusi frame default: Final -> Demo -> None tanpa fallback ke root."""

    def test_resolve_default_frame_picks_final_when_present(self, tmp_path: Path, monkeypatch):
        final_dir = tmp_path / "final"
        demo_dir = tmp_path / "demo"
        final_dir.mkdir()
        demo_dir.mkdir()

        final_file = final_dir / "frame_desain_a.png"
        final_file.touch()
        demo_file = demo_dir / "demo_frame_a.png"
        demo_file.touch()

        monkeypatch.setattr("src.gui.app.FINAL_BORDERS_DIR", final_dir)
        monkeypatch.setattr("src.gui.app.DEMO_BORDERS_DIR", demo_dir)

        resolved = resolve_default_frame("frame_desain_a.png", "demo_frame_a.png")
        assert resolved == final_file
        assert resolved.parent == final_dir

    def test_resolve_default_frame_picks_demo_when_final_missing(self, tmp_path: Path, monkeypatch):
        final_dir = tmp_path / "final"
        demo_dir = tmp_path / "demo"
        final_dir.mkdir()
        demo_dir.mkdir()

        demo_file = demo_dir / "demo_frame_a.png"
        demo_file.touch()

        monkeypatch.setattr("src.gui.app.FINAL_BORDERS_DIR", final_dir)
        monkeypatch.setattr("src.gui.app.DEMO_BORDERS_DIR", demo_dir)

        resolved = resolve_default_frame("frame_desain_a.png", "demo_frame_a.png")
        assert resolved == demo_file
        assert resolved.parent == demo_dir

    def test_resolve_default_frame_returns_none_when_both_missing(self, tmp_path: Path, monkeypatch):
        final_dir = tmp_path / "final"
        demo_dir = tmp_path / "demo"
        final_dir.mkdir()
        demo_dir.mkdir()

        monkeypatch.setattr("src.gui.app.FINAL_BORDERS_DIR", final_dir)
        monkeypatch.setattr("src.gui.app.DEMO_BORDERS_DIR", demo_dir)

        resolved = resolve_default_frame("frame_desain_a.png", "demo_frame_a.png")
        assert resolved is None

    def test_resolve_default_frame_never_falls_back_to_root(self, tmp_path: Path, monkeypatch):
        # Skenario: root memiliki file, tetapi final dan demo kosong
        final_dir = tmp_path / "final"
        demo_dir = tmp_path / "demo"
        root_dir = tmp_path
        final_dir.mkdir()
        demo_dir.mkdir()

        root_file = root_dir / "frame_desain_a.png"
        root_file.touch()

        monkeypatch.setattr("src.gui.app.FINAL_BORDERS_DIR", final_dir)
        monkeypatch.setattr("src.gui.app.DEMO_BORDERS_DIR", demo_dir)

        resolved = resolve_default_frame("frame_desain_a.png", "demo_frame_a.png")
        # Harus tetap None dan tidak mengambil dari root_file
        assert resolved is None
