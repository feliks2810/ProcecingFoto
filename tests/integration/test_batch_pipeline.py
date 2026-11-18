"""
Integration test suite untuk Batch Processing Pipeline dan Reporting.
"""

import json
import csv
import threading
from pathlib import Path
import pytest
from PIL import Image, ImageDraw

from src.config.models import BatchConfig, SingleBatchConfig, SlotCoordinates
from src.pipeline.runner import BatchPipelineRunner
from src.pipeline.scanner import scan_folder_photos
from tests.conftest import compute_sha256


@pytest.fixture
def dual_frame_setup(tmp_path: Path):
    """
    Menyiapkan dua desain frame PNG transparan yang berbeda:
    - Frame A (1000x1000): Bingkai merah dengan lubang transparan (200, 200, 600, 600)
    - Frame B (1200x800): Bingkai biru dengan lubang transparan (100, 100, 1000, 600)
    """
    frame_dir = tmp_path / "test_frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    # Frame Desain A
    frame_a_path = frame_dir / "frame_a.png"
    img_a = Image.new("RGBA", (1000, 1000), (255, 0, 0, 255))
    draw_a = ImageDraw.Draw(img_a)
    draw_a.rectangle([200, 200, 800, 800], fill=(0, 0, 0, 0))
    img_a.save(frame_a_path, "PNG")

    # Frame Desain B
    frame_b_path = frame_dir / "frame_b.png"
    img_b = Image.new("RGBA", (1200, 800), (0, 0, 255, 255))
    draw_b = ImageDraw.Draw(img_b)
    draw_b.rectangle([100, 100, 1100, 700], fill=(0, 0, 0, 0))
    img_b.save(frame_b_path, "PNG")

    slot_a = SlotCoordinates(x=200, y=200, width=600, height=600)
    slot_b = SlotCoordinates(x=100, y=100, width=1000, height=600)

    return {
        "frame_a": frame_a_path,
        "slot_a": slot_a,
        "frame_b": frame_b_path,
        "slot_b": slot_b,
    }


class TestBatchPipelineIntegration:
    """Pengujian integrasi batch runner, fault-tolerance, dan pelaporan."""

    def test_batch_with_portrait_and_landscape_photos(self, dual_frame_setup, tmp_path: Path):
        """Memproses batch yang memuat campuran foto portrait dan landscape."""
        input_dir = tmp_path / "mixed_inputs"
        input_dir.mkdir()
        out_dir = tmp_path / "mixed_outputs"

        # Buat 2 portrait dan 2 landscape
        photos = [
            input_dir / "portrait_1.jpg",
            input_dir / "portrait_2.jpg",
            input_dir / "landscape_1.jpg",
            input_dir / "landscape_2.jpg",
        ]
        Image.new("RGB", (600, 900), (50, 50, 200)).save(photos[0], "JPEG")
        Image.new("RGB", (800, 1200), (70, 70, 220)).save(photos[1], "JPEG")
        Image.new("RGB", (1200, 800), (20, 180, 50)).save(photos[2], "JPEG")
        Image.new("RGB", (1600, 900), (30, 200, 80)).save(photos[3], "JPEG")

        cfg = BatchConfig(
            output_folder=out_dir,
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Campuran",
                input_folder=input_dir,
                frame_path=dual_frame_setup["frame_a"],
                slot_coordinates=dual_frame_setup["slot_a"]
            ),
            batch_2=SingleBatchConfig(batch_id="batch_2", name="Kosong")
        )

        runner = BatchPipelineRunner(cfg)
        report = runner.run()

        assert report.total_found == 4
        assert report.total_success == 4
        assert report.total_failed == 0

        # Periksa file output
        batch_1_out = cfg.get_output_dir_for_batch("batch_1")
        output_files = list(batch_1_out.glob("*.png"))
        assert len(output_files) == 4

    def test_dual_batch_with_different_frames(self, dual_frame_setup, tmp_path: Path):
        """Menjalankan 2 batch dengan input folder dan template frame berbeda."""
        in_1 = tmp_path / "in_batch_1"
        in_2 = tmp_path / "in_batch_2"
        in_1.mkdir()
        in_2.mkdir()
        out_dir = tmp_path / "dual_outputs"

        # 3 foto di folder 1, 2 foto di folder 2
        for i in range(3):
            p = in_1 / f"b1_foto_{i}.jpg"
            Image.new("RGB", (400, 400), (10, 20, 30)).save(p, "JPEG")

        for i in range(2):
            p = in_2 / f"b2_foto_{i}.jpg"
            Image.new("RGB", (400, 400), (40, 50, 60)).save(p, "JPEG")

        cfg = BatchConfig(
            output_folder=out_dir,
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch 1",
                input_folder=in_1,
                frame_path=dual_frame_setup["frame_a"],
                slot_coordinates=dual_frame_setup["slot_a"]
            ),
            batch_2=SingleBatchConfig(
                batch_id="batch_2",
                name="Batch 2",
                input_folder=in_2,
                frame_path=dual_frame_setup["frame_b"],
                slot_coordinates=dual_frame_setup["slot_b"]
            )
        )

        runner = BatchPipelineRunner(cfg)
        report = runner.run()

        assert report.total_found == 5
        assert report.total_success == 5
        assert report.total_failed == 0

        # Verifikasi pemisahan output
        out_1 = cfg.get_output_dir_for_batch("batch_1")
        out_2 = cfg.get_output_dir_for_batch("batch_2")
        assert len(list(out_1.glob("*.png"))) == 3
        assert len(list(out_2.glob("*.png"))) == 2

    def test_empty_folder_handling(self, dual_frame_setup, tmp_path: Path):
        """Folder input kosong harus ditangani tanpa error unhandled."""
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        cfg = BatchConfig(
            output_folder=tmp_path / "out",
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Kosong",
                input_folder=empty_dir,
                frame_path=dual_frame_setup["frame_a"],
                slot_coordinates=dual_frame_setup["slot_a"]
            )
        )

        runner = BatchPipelineRunner(cfg)
        report = runner.run()

        assert report.total_found == 0
        assert report.total_processed == 0
        assert report.total_success == 0
        assert report.total_failed == 0

    def test_max_photos_limit_enforced(self, tmp_path: Path):
        """Memverifikasi batas maksimal 250 foto dipatuhi saat folder berisi lebih dari 250 foto."""
        large_dir = tmp_path / "large_input"
        large_dir.mkdir()

        total_created = 265
        for i in range(total_created):
            p = large_dir / f"foto_{i:03d}.jpg"
            p.write_bytes(b"dummy")

        scanned = scan_folder_photos(large_dir, max_photos=250)
        assert len(scanned) == 250

    def test_partially_corrupt_photos_fault_tolerant(self, dual_frame_setup, tmp_path: Path):
        """Satu atau lebih foto korup tidak boleh menghentikan pemrosesan batch."""
        test_dir = tmp_path / "partially_corrupt"
        test_dir.mkdir()

        # 2 foto valid
        Image.new("RGB", (200, 200), (1, 2, 3)).save(test_dir / "valid_1.jpg", "JPEG")
        Image.new("RGB", (200, 200), (4, 5, 6)).save(test_dir / "valid_2.jpg", "JPEG")

        # 1 file 0-byte
        (test_dir / "corrupt_zero.jpg").write_bytes(b"")

        # 1 file teks yang dinamai .png
        (test_dir / "corrupt_fake.png").write_text("bukan sebuah gambar")

        cfg = BatchConfig(
            output_folder=tmp_path / "out_tolerant",
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Toleran",
                input_folder=test_dir,
                frame_path=dual_frame_setup["frame_a"],
                slot_coordinates=dual_frame_setup["slot_a"]
            )
        )

        runner = BatchPipelineRunner(cfg)
        report = runner.run()

        assert report.total_found == 4
        assert report.total_success == 2
        assert report.total_failed == 2
        assert len(report.batches["batch_1"].failed_items) == 2

    def test_batch_cancellation(self, dual_frame_setup, tmp_path: Path):
        """Pembatalan batch di tengah jalan menghentikan proses secara anggun."""
        cancel_dir = tmp_path / "cancel_inputs"
        cancel_dir.mkdir()
        out_dir = tmp_path / "cancel_outputs"

        for i in range(10):
            p = cancel_dir / f"foto_{i:02d}.jpg"
            Image.new("RGB", (200, 200), (i * 10, i * 10, 50)).save(p, "JPEG")

        cancel_event = threading.Event()

        # Callback yang memicu pembatalan setelah 3 foto selesai
        def on_prog(completed, total, succ, fail, fname, eta):
            if completed >= 3:
                cancel_event.set()

        cfg = BatchConfig(
            output_folder=out_dir,
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Dibatalkan",
                input_folder=cancel_dir,
                frame_path=dual_frame_setup["frame_a"],
                slot_coordinates=dual_frame_setup["slot_a"]
            )
        )

        runner = BatchPipelineRunner(cfg, on_progress=on_prog, cancel_event=cancel_event)
        report = runner.run()

        assert report.is_cancelled is True
        # Total yang diproses harus berhenti di sekitar 3 foto (kurang dari 10)
        assert report.total_processed < 10

        # Pastikan tidak ada file sementara .tmp_* tertinggal
        out_sub = cfg.get_output_dir_for_batch("batch_1")
        temp_files = list(out_sub.glob(".tmp_*"))
        assert len(temp_files) == 0

    def test_pre_existing_output_files_not_overwritten(self, dual_frame_setup, tmp_path: Path):
        """Memastikan file output yang sudah ada tidak tertimpa."""
        in_dir = tmp_path / "existing_in"
        in_dir.mkdir()
        out_dir = tmp_path / "existing_out"
        out_sub = out_dir / "batch_frame_1"
        out_sub.mkdir(parents=True, exist_ok=True)

        photo = in_dir / "foto_sample.jpg"
        Image.new("RGB", (300, 300), (10, 20, 30)).save(photo, "JPEG")

        # Buat file output yang sudah ada lebih dulu
        existing_target = out_sub / "foto_sample_framed.png"
        existing_target.write_text("konten_asli_terlindungi")

        cfg = BatchConfig(
            output_folder=out_dir,
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Existing Check",
                input_folder=in_dir,
                frame_path=dual_frame_setup["frame_a"],
                slot_coordinates=dual_frame_setup["slot_a"]
            )
        )

        runner = BatchPipelineRunner(cfg)
        report = runner.run()

        assert report.total_success == 1

        # File awal tidak boleh berubah
        assert existing_target.read_text() == "konten_asli_terlindungi"

        # File baru harus disimpan dengan sufiks unik _1
        new_output = out_sub / "foto_sample_framed_1.png"
        assert new_output.exists()

    def test_source_files_sha256_unmodified(self, dual_frame_setup, tmp_path: Path):
        """Memastikan seluruh foto sumber sama sekali tidak tersentuh (SHA-256 identik)."""
        safe_in = tmp_path / "safe_inputs"
        safe_in.mkdir()
        photos = []
        for i in range(5):
            p = safe_in / f"safe_pic_{i}.jpg"
            Image.new("RGB", (400, 400), (i * 20, 100, 150)).save(p, "JPEG")
            photos.append(p)

        hashes_before = {p: compute_sha256(p) for p in photos}

        cfg = BatchConfig(
            output_folder=tmp_path / "safe_out",
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Safety Verification",
                input_folder=safe_in,
                frame_path=dual_frame_setup["frame_a"],
                slot_coordinates=dual_frame_setup["slot_a"]
            )
        )

        runner = BatchPipelineRunner(cfg)
        report = runner.run()
        assert report.total_success == len(photos)

        # Verifikasi bitwise
        for p in photos:
            assert p.exists()
            assert compute_sha256(p) == hashes_before[p], f"File sumber {p.name} termodifikasi!"

    def test_report_export_json_and_csv(self, dual_frame_setup, tmp_path: Path):
        """Menguji ekspor laporan ringkasan ke format JSON dan CSV."""
        in_dir = tmp_path / "report_in"
        in_dir.mkdir()
        p = in_dir / "sample.jpg"
        Image.new("RGB", (200, 200), (50, 50, 50)).save(p, "JPEG")

        cfg = BatchConfig(
            output_folder=tmp_path / "report_out",
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch Export Test",
                input_folder=in_dir,
                frame_path=dual_frame_setup["frame_a"],
                slot_coordinates=dual_frame_setup["slot_a"]
            )
        )

        runner = BatchPipelineRunner(cfg)
        report = runner.run()

        json_file = tmp_path / "report.json"
        csv_file = tmp_path / "report.csv"

        report.export_json(json_file)
        report.export_csv(csv_file)

        assert json_file.exists()
        assert csv_file.exists()

        # Validasi struktur JSON
        with open(json_file, "r", encoding="utf-8") as f:
            j_data = json.load(f)
            assert "summary" in j_data
            assert j_data["summary"]["total_success"] == 1
            assert "batches" in j_data
            assert "batch_1" in j_data["batches"]

        # Validasi baris CSV
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["status"] == "SUCCESS"
            assert rows[0]["batch_id"] == "batch_1"
