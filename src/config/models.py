"""
Data model Pydantic untuk konfigurasi dan pelaporan PhotoFrameProcessor.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator

from src.config.settings import (
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_PHOTOS_PER_BATCH,
    DEFAULT_SUBFOLDER_BATCH_1,
    DEFAULT_SUBFOLDER_BATCH_2,
    SUPPORTED_FRAME_EXTENSIONS,
)


class SlotCoordinates(BaseModel):
    """
    Model koordinat area jendela/slot foto pada frame PNG.
    Semua koordinat dalam satuan piksel relatif terhadap dimensi kanvas frame asli.
    """
    x: int = Field(..., ge=0, description="Posisi horizontal sudut kiri atas slot (piksel >= 0)")
    y: int = Field(..., ge=0, description="Posisi vertikal sudut kiri atas slot (piksel >= 0)")
    width: int = Field(..., gt=0, description="Lebar area slot foto (piksel > 0)")
    height: int = Field(..., gt=0, description="Tinggi area slot foto (piksel > 0)")

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Mengembalikan (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    def to_box(self) -> Tuple[int, int, int, int]:
        """Mengembalikan (left, top, right, bottom)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def aspect_ratio(self) -> float:
        """Rasio aspek (width / height) dari slot target."""
        return self.width / self.height if self.height > 0 else 1.0


class SingleBatchConfig(BaseModel):
    """
    Konfigurasi satu batch pemrosesan foto dengan frame tertentu.
    """
    batch_id: str = Field(..., description="Identifier unik batch (e.g. 'batch_1' atau 'batch_2')")
    name: str = Field(..., description="Nama deskriptif batch")
    input_folder: Optional[Path] = Field(default=None, description="Path folder sumber foto")
    frame_path: Optional[Path] = Field(default=None, description="Path file frame PNG transparan")
    slot_coordinates: Optional[SlotCoordinates] = Field(
        default=None,
        description="Koordinat penempatan foto pada frame (jika None, menggunakan deteksi otomatis atau dimensi penuh frame)"
    )
    max_photos: int = Field(
        default=DEFAULT_PHOTOS_PER_BATCH,
        ge=1,
        description="Jumlah maksimal foto yang diproses dalam batch ini"
    )

    @field_validator("frame_path")
    @classmethod
    def validate_frame_extension(cls, v: Optional[Path]) -> Optional[Path]:
        if v is not None:
            if v.suffix.lower() not in SUPPORTED_FRAME_EXTENSIONS:
                raise ValueError(
                    f"Frame harus berekstensi {SUPPORTED_FRAME_EXTENSIONS}, format ditemukan: {v.suffix}"
                )
        return v


class BatchConfig(BaseModel):
    """
    Konfigurasi menyeluruh untuk dua batch pemrosesan frame foto (total target 500 foto).
    Mendukung 2 input folder manual, 2 desain frame PNG, koordinat slot terpisah,
    serta output terpusat yang aman (non-destructive).
    """
    batch_1: SingleBatchConfig = Field(
        default_factory=lambda: SingleBatchConfig(
            batch_id="batch_1",
            name="Batch 1 (Frame Desain A)",
            max_photos=DEFAULT_PHOTOS_PER_BATCH,
        )
    )
    batch_2: SingleBatchConfig = Field(
        default_factory=lambda: SingleBatchConfig(
            batch_id="batch_2",
            name="Batch 2 (Frame Desain B)",
            max_photos=DEFAULT_PHOTOS_PER_BATCH,
        )
    )
    output_folder: Path = Field(..., description="Direktori target penyimpanan hasil komposit")
    create_subfolders: bool = Field(
        default=True,
        description="Apakah hasil batch disimpan di subfolder terpisah (batch_frame_1 & batch_frame_2)"
    )
    subfolder_batch_1: str = Field(default=DEFAULT_SUBFOLDER_BATCH_1)
    subfolder_batch_2: str = Field(default=DEFAULT_SUBFOLDER_BATCH_2)
    export_format: str = Field(default="PNG", description="Format citra hasil: 'PNG' atau 'JPEG'")
    output_quality: int = Field(
        default=DEFAULT_OUTPUT_QUALITY,
        ge=1,
        le=100,
        description="Kualitas output kompresi JPEG/WebP (1-100)"
    )

    @field_validator("export_format")
    @classmethod
    def validate_export_format(cls, v: str) -> str:
        fmt = v.upper()
        if fmt not in {"PNG", "JPEG", "JPG"}:
            raise ValueError(f"Format export tidak didukung: {v}. Gunakan PNG atau JPEG.")
        return "JPEG" if fmt == "JPG" else fmt

    def get_output_dir_for_batch(self, batch_id: str) -> Path:
        """Mendapatkan path folder output tujuan untuk batch tertentu."""
        if not self.create_subfolders:
            return self.output_folder
        if batch_id == "batch_1":
            return self.output_folder / self.subfolder_batch_1
        elif batch_id == "batch_2":
            return self.output_folder / self.subfolder_batch_2
        return self.output_folder / batch_id


class FileResult(BaseModel):
    """
    Model representasi hasil pemrosesan sebuah file citra.
    """
    source_file: Path = Field(..., description="Path file foto sumber asli")
    output_file: Optional[Path] = Field(default=None, description="Path file hasil komposit yang disimpan")
    batch_id: str = Field(..., description="Batch pemroses file ini ('batch_1' atau 'batch_2')")
    success: bool = Field(..., description="Status keberhasilan pemrosesan file")
    error_message: Optional[str] = Field(default=None, description="Pesan kegagalan jika success=False")
    execution_time_ms: float = Field(default=0.0, ge=0.0, description="Durasi proses file dalam milidetik")


class BatchSummaryReport(BaseModel):
    """
    Laporan rekapitulasi akhir dari eksekusi batch 500 foto.
    """
    total_photos_scanned: int = Field(default=0, ge=0)
    total_success: int = Field(default=0, ge=0)
    total_failed: int = Field(default=0, ge=0)
    is_cancelled: bool = Field(default=False)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration_seconds: float = Field(default=0.0, ge=0.0)
    results: List[FileResult] = Field(default_factory=list)

    @property
    def throughput_fps(self) -> float:
        """Menghitung throughput rata-rata pemrosesan (foto per detik)."""
        if self.total_duration_seconds > 0 and self.total_success > 0:
            return round(self.total_success / self.total_duration_seconds, 2)
        return 0.0
