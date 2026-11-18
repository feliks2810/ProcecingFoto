"""
Unit test suite khusus untuk verifikasi Konfigurasi Persisten PhotoFrameProcessor.
Menguji penyimpanan, pemuatan ulang, validasi JSON rusak, dan preservasi koordinat serta format ekspor.
"""

import json
from pathlib import Path
import pytest

from src.config.models import BatchConfig, SingleBatchConfig, SlotCoordinates
from src.config.persistence import save_user_config, load_user_config


class TestPersistentConfiguration:
    """Pengujian komprehensif mekanisme penyimpanan dan pemuatan user_config.json."""

    def test_save_configuration_to_json(self, tmp_path: Path):
        """Memverifikasi fungsi save_user_config menulis file JSON yang valid."""
        cfg_file = tmp_path / "test_user_cfg.json"

        config = BatchConfig(
            output_folder=tmp_path / "custom_outputs",
            export_format="JPEG",
            output_quality=92,
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Batch 1 Wedding",
                input_folder=tmp_path / "photos_1",
                frame_path=tmp_path / "frame_a.png",
                slot_coordinates=SlotCoordinates(x=120, y=140, width=800, height=1000),
                max_photos=250
            ),
            batch_2=SingleBatchConfig(
                batch_id="batch_2",
                name="Batch 2 Reception",
                input_folder=tmp_path / "photos_2",
                frame_path=tmp_path / "frame_b.png",
                slot_coordinates=SlotCoordinates(x=50, y=60, width=1200, height=800),
                max_photos=250
            )
        )

        success = save_user_config(config, cfg_file)
        assert success is True
        assert cfg_file.exists()

        # Verifikasi bahwa file adalah JSON valid
        with open(cfg_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            assert raw_data["export_format"] == "JPEG"
            assert raw_data["output_quality"] == 92
            assert raw_data["batch_1"]["slot_coordinates"]["x"] == 120
            assert raw_data["batch_2"]["slot_coordinates"]["width"] == 1200

    def test_load_configuration_after_app_reopen(self, tmp_path: Path):
        """Memverifikasi konfigurasi dapat dimuat kembali secara identik seperti saat aplikasi dibuka kembali."""
        cfg_file = tmp_path / "reopen_cfg.json"

        original_slot_1 = SlotCoordinates(x=175, y=210, width=750, height=950)
        original_slot_2 = SlotCoordinates(x=80, y=90, width=1100, height=700)

        initial_config = BatchConfig(
            output_folder=tmp_path / "wedding_framed",
            export_format="PNG",
            output_quality=95,
            create_subfolders=True,
            subfolder_batch_1="sesi_akad",
            subfolder_batch_2="sesi_resepsi",
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Akad",
                input_folder=tmp_path / "raw_akad",
                frame_path=tmp_path / "frame_akad.png",
                slot_coordinates=original_slot_1
            ),
            batch_2=SingleBatchConfig(
                batch_id="batch_2",
                name="Resepsi",
                input_folder=tmp_path / "raw_resepsi",
                frame_path=tmp_path / "frame_resepsi.png",
                slot_coordinates=original_slot_2
            )
        )

        save_user_config(initial_config, cfg_file)

        # Simulasikan membuka aplikasi kembali dengan membaca file konfigurasi
        reloaded_config = load_user_config(cfg_file)

        assert reloaded_config is not None
        assert reloaded_config.output_folder == tmp_path / "wedding_framed"
        assert reloaded_config.export_format == "PNG"
        assert reloaded_config.subfolder_batch_1 == "sesi_akad"
        assert reloaded_config.subfolder_batch_2 == "sesi_resepsi"

        # Verifikasi koordinat Batch 1
        b1_slot = reloaded_config.batch_1.slot_coordinates
        assert b1_slot.x == 175
        assert b1_slot.y == 210
        assert b1_slot.width == 750
        assert b1_slot.height == 950

        # Verifikasi koordinat Batch 2
        b2_slot = reloaded_config.batch_2.slot_coordinates
        assert b2_slot.x == 80
        assert b2_slot.y == 90
        assert b2_slot.width == 1100
        assert b2_slot.height == 700

    def test_validate_malformed_syntax_json(self, tmp_path: Path):
        """Memverifikasi penanganan jika file JSON mengalami korupsi sintaks (tidak melempar exception fatal)."""
        corrupted_file = tmp_path / "corrupted_syntax.json"
        corrupted_file.write_text("{ ini adalah teks rusak dan bukan JSON valid :::", encoding="utf-8")

        loaded = load_user_config(corrupted_file)
        assert loaded is None

    def test_validate_schema_invalid_json(self, tmp_path: Path):
        """Memverifikasi penanganan jika JSON valid tetapi tidak sesuai skema Pydantic (misal koordinat negatif)."""
        invalid_schema_file = tmp_path / "invalid_schema.json"
        # Koordinat x bernilai negatif (-500) yang dilarang oleh validator Pydantic
        invalid_data = {
            "output_folder": str(tmp_path / "out"),
            "batch_1": {
                "batch_id": "batch_1",
                "name": "Invalid Batch",
                "slot_coordinates": {
                    "x": -500,
                    "y": 100,
                    "width": 200,
                    "height": 200
                }
            }
        }
        invalid_schema_file.write_text(json.dumps(invalid_data), encoding="utf-8")

        loaded = load_user_config(invalid_schema_file)
        assert loaded is None

    def test_preserve_slot_coordinates_and_export_format(self, tmp_path: Path):
        """Memastikan perubahan spesifik pada slot koordinat dan format ekspor dipertahankan secara akurat."""
        cfg_file = tmp_path / "preserve_test.json"

        config = BatchConfig(
            output_folder=tmp_path / "out_preserve",
            export_format="JPEG",
            output_quality=88,
            batch_1=SingleBatchConfig(
                batch_id="batch_1",
                name="Preserve Test",
                slot_coordinates=SlotCoordinates(x=333, y=444, width=555, height=666)
            )
        )

        save_user_config(config, cfg_file)
        loaded = load_user_config(cfg_file)

        assert loaded is not None
        assert loaded.export_format == "JPEG"
        assert loaded.output_quality == 88
        assert loaded.batch_1.slot_coordinates.to_tuple() == (333, 444, 555, 666)
