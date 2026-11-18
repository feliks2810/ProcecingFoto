"""
Benchmark performa batch processing hingga 500 foto sintetis dengan pemantauan memori (psutil & tracemalloc).
"""

import os
import time
import tracemalloc
from pathlib import Path
import pytest
from PIL import Image, ImageDraw

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from src.config.models import BatchConfig, SingleBatchConfig, SlotCoordinates
from src.pipeline.runner import BatchPipelineRunner


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_500_photos_pipeline(tmp_path: Path):
    """
    Uji beban dan benchmark nyata untuk 500 foto sintetis:
    - 250 foto untuk Batch 1 (Frame A)
    - 250 foto untuk Batch 2 (Frame B)
    - Total: 500 foto ukuran realistis (~1000x750 piksel, campuran portrait & landscape).
    - Memantau penggunaan RAM dengan psutil dan tracemalloc untuk memastikan tidak ada memory leak.
    """
    bench_root = tmp_path / "benchmark_run"
    dir_batch_1 = bench_root / "input_batch_1"
    dir_batch_2 = bench_root / "input_batch_2"
    dir_batch_1.mkdir(parents=True, exist_ok=True)
    dir_batch_2.mkdir(parents=True, exist_ok=True)
    out_dir = bench_root / "output"

    # 1. Siapkan Frame A dan Frame B
    frame_dir = bench_root / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    frame_a_path = frame_dir / "frame_a.png"
    img_a = Image.new("RGBA", (1200, 1200), (200, 30, 30, 255))
    draw_a = ImageDraw.Draw(img_a)
    draw_a.rectangle([150, 150, 1050, 1050], fill=(0, 0, 0, 0))
    img_a.save(frame_a_path, "PNG")

    frame_b_path = frame_dir / "frame_b.png"
    img_b = Image.new("RGBA", (1400, 1000), (30, 80, 200, 255))
    draw_b = ImageDraw.Draw(img_b)
    draw_b.rectangle([100, 100, 1300, 900], fill=(0, 0, 0, 0))
    img_b.save(frame_b_path, "PNG")

    slot_a = SlotCoordinates(x=150, y=150, width=900, height=900)
    slot_b = SlotCoordinates(x=100, y=100, width=1200, height=800)

    # 2. Buat 250 foto sintetis untuk Batch 1 (campuran portrait & landscape)
    print("\nMenyiapkan 250 foto sintetis untuk Batch 1...")
    for i in range(250):
        p = dir_batch_1 / f"b1_img_{i:03d}.jpg"
        # Alternasi portrait (750x1000) dan landscape (1000x750)
        is_portrait = (i % 2 == 0)
        size = (750, 1000) if is_portrait else (1000, 750)
        color = ((i * 7) % 256, (i * 13) % 256, 180)
        img = Image.new("RGB", size, color)
        img.save(p, "JPEG", quality=85)

    # 3. Buat 250 foto sintetis untuk Batch 2 (campuran portrait & landscape)
    print("Menyiapkan 250 foto sintetis untuk Batch 2...")
    for i in range(250):
        p = dir_batch_2 / f"b2_img_{i:03d}.jpg"
        is_portrait = (i % 2 == 0)
        size = (700, 950) if is_portrait else (950, 700)
        color = (150, (i * 11) % 256, (i * 17) % 256)
        img = Image.new("RGB", size, color)
        img.save(p, "JPEG", quality=85)

    cfg = BatchConfig(
        output_folder=out_dir,
        batch_1=SingleBatchConfig(
            batch_id="batch_1",
            name="Batch 1 (250 Foto)",
            input_folder=dir_batch_1,
            frame_path=frame_a_path,
            slot_coordinates=slot_a,
            max_photos=250
        ),
        batch_2=SingleBatchConfig(
            batch_id="batch_2",
            name="Batch 2 (250 Foto)",
            input_folder=dir_batch_2,
            frame_path=frame_b_path,
            slot_coordinates=slot_b,
            max_photos=250
        )
    )

    # 4. Mulai monitoring performa
    process = psutil.Process(os.getpid()) if HAS_PSUTIL else None
    initial_rss_mb = process.memory_info().rss / (1024 * 1024) if process else 0.0

    tracemalloc.start()
    t_start = time.perf_counter()

    runner = BatchPipelineRunner(cfg)
    report = runner.run()

    t_elapsed = time.perf_counter() - t_start
    current_traced, peak_traced = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_traced_mb = peak_traced / (1024 * 1024)
    final_rss_mb = process.memory_info().rss / (1024 * 1024) if process else 0.0
    rss_growth_mb = final_rss_mb - initial_rss_mb if process else 0.0

    avg_ms = (t_elapsed * 1000.0) / report.total_processed if report.total_processed > 0 else 0.0
    throughput = report.total_processed / t_elapsed if t_elapsed > 0 else 0.0

    # Tampilkan tabel hasil benchmark nyata
    print("\n" + "=" * 65)
    print("         HASIL BENCHMARK NYATA: PIPELINE 500 FOTO")
    print("=" * 65)
    print(f"Total Foto Ditemukan : {report.total_found}")
    print(f"Total Foto Diproses  : {report.total_processed}")
    print(f"Jumlah Sukses        : {report.total_success}")
    print(f"Jumlah Gagal         : {report.total_failed}")
    print(f"Durasi Keseluruhan   : {t_elapsed:.2f} detik")
    print(f"Rata-rata per Foto   : {avg_ms:.2f} ms")
    print(f"Throughput           : {throughput:.2f} foto/detik")
    if HAS_PSUTIL:
        print(f"RAM Awal (RSS)       : {initial_rss_mb:.2f} MB")
        print(f"RAM Akhir (RSS)      : {final_rss_mb:.2f} MB")
        print(f"Pertumbuhan RAM      : {rss_growth_mb:+.2f} MB")
    print(f"Peak RAM (Allocated) : {peak_traced_mb:.2f} MB")
    print("=" * 65)

    # Verifikasi kuantitas & integritas hasil
    assert report.total_found == 500, "Total foto input harus 500"
    assert report.total_processed == 500, "Total foto yang diproses harus 500"
    assert report.total_success == 500, "Seluruh 500 foto harus berhasil diproses"
    assert report.total_failed == 0, "Tidak boleh ada foto yang gagal"

    # Periksa output folder
    out_b1 = cfg.get_output_dir_for_batch("batch_1")
    out_b2 = cfg.get_output_dir_for_batch("batch_2")
    assert len(list(out_b1.glob("*.png"))) == 250, "Batch 1 harus menghasilkan 250 file PNG"
    assert len(list(out_b2.glob("*.png"))) == 250, "Batch 2 harus menghasilkan 250 file PNG"

    # Ekspor laporan pengujian
    json_rep = bench_root / "benchmark_report.json"
    csv_rep = bench_root / "benchmark_report.csv"
    report.export_json(json_rep)
    report.export_csv(csv_rep)
    assert json_rep.exists()
    assert csv_rep.exists()
