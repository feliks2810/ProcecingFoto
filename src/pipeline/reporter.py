"""
Modul pelaporan hasil eksekusi batch pipeline (JSON dan CSV export).
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.config.models import FileResult


class BatchBreakdown(BaseModel):
    """Ringkasan statistik untuk satu batch spesifik."""
    batch_id: str
    name: str
    input_folder: Optional[str] = None
    frame_path: Optional[str] = None
    output_folder: str
    total_found: int = 0
    total_processed: int = 0
    total_success: int = 0
    total_failed: int = 0
    duration_seconds: float = 0.0
    avg_ms_per_photo: float = 0.0
    failed_items: List[Dict[str, str]] = Field(default_factory=list)


class PipelineReport(BaseModel):
    """Laporan komprehensif seluruh eksekusi batch pipeline."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_found: int = 0
    total_processed: int = 0
    total_success: int = 0
    total_failed: int = 0
    is_cancelled: bool = False
    total_duration_seconds: float = 0.0
    avg_ms_per_photo: float = 0.0
    overall_throughput_fps: float = 0.0
    batches: Dict[str, BatchBreakdown] = Field(default_factory=dict)
    results: List[FileResult] = Field(default_factory=list)

    def export_json(self, target_path: Path) -> Path:
        """
        Mengekspor laporan ringkasan dalam format JSON yang terstruktur.
        """
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "timestamp": self.timestamp,
            "summary": {
                "total_found": self.total_found,
                "total_processed": self.total_processed,
                "total_success": self.total_success,
                "total_failed": self.total_failed,
                "is_cancelled": self.is_cancelled,
                "total_duration_seconds": round(self.total_duration_seconds, 2),
                "avg_ms_per_photo": round(self.avg_ms_per_photo, 2),
                "overall_throughput_fps": round(self.overall_throughput_fps, 2),
            },
            "batches": {
                b_id: {
                    "name": b_info.name,
                    "input_folder": b_info.input_folder,
                    "frame_path": b_info.frame_path,
                    "output_folder": b_info.output_folder,
                    "total_found": b_info.total_found,
                    "total_processed": b_info.total_processed,
                    "total_success": b_info.total_success,
                    "total_failed": b_info.total_failed,
                    "duration_seconds": round(b_info.duration_seconds, 2),
                    "avg_ms_per_photo": round(b_info.avg_ms_per_photo, 2),
                    "failed_items": b_info.failed_items,
                }
                for b_id, b_info in self.batches.items()
            },
            "failures": [
                {
                    "source_file": str(r.source_file),
                    "batch_id": r.batch_id,
                    "error_message": r.error_message,
                }
                for r in self.results
                if not r.success
            ]
        }

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return target

    def export_csv(self, target_path: Path) -> Path:
        """
        Mengekspor data hasil per-file foto ke dalam format file CSV.
        """
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "batch_id",
            "source_file_name",
            "source_file_path",
            "output_file_path",
            "status",
            "execution_time_ms",
            "error_message"
        ]

        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.results:
                writer.writerow({
                    "batch_id": r.batch_id,
                    "source_file_name": r.source_file.name,
                    "source_file_path": str(r.source_file),
                    "output_file_path": str(r.output_file) if r.output_file else "",
                    "status": "SUCCESS" if r.success else "FAILED",
                    "execution_time_ms": r.execution_time_ms,
                    "error_message": r.error_message or "",
                })

        return target
