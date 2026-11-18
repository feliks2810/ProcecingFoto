# PhotoFrameProcessor Studio 📸🖼️

**PhotoFrameProcessor** adalah aplikasi desktop Windows modern berkinerja tinggi untuk memproses pembingkaian foto digital secara otomatis ke dalam template bingkai PNG transparan. Dirancang khusus untuk memproses hingga **500 foto** dalam satu siklus kerja dengan pembagian dua batch desain bingkai yang berbeda (masing-masing 250 foto).

---

## 🌟 Fitur Utama

1. **Pemrosesan Dual-Batch (500 Foto Sekaligus)**:
   * **Batch 1**: Folder foto A dipasangkan dengan Desain Frame PNG A (maksimal 250 foto).
   * **Batch 2**: Folder foto B dipasangkan dengan Desain Frame PNG B (maksimal 250 foto).
2. **Interactive Photo Placement Editor**:
   * Penentuan koordinat slot foto secara visual interaktif dengan klik-drag kanvas atau manipulasi *resize handles*.
   * Input numerik presisi untuk koordinat **X**, **Y**, **Lebar (W)**, dan **Tinggi (H)**.
   * Fitur **Deteksi Lubang Otomatis** (*Auto-detect Transparent Hole*) berbasis analisis saluran alpha frame.
   * Transformasi rasio visual kanvas ke resolusi piksel fisik frame asli yang 100% presisi.
3. **Smart Crop & Penjagaan Rasio Aspek**:
   * Mendukung orientasi foto campuran (**Portrait**, **Landscape**, dan **Square**) tanpa distorsi lonjong.
   * Menggunakan algoritma *Aspect Fill / Cover* dengan pemotongan simetris di tengah (*center crop*) dan resampling **LANCZOS** berkualitas tinggi.
4. **Normalisasi Orientasi EXIF Otomatis**:
   * Membaca metadata orientasi kamera (EXIF tag 1–8) dan mengoreksi rotasi fisik secara otomatis sebelum proses *framing*.
5. **Alpha Compositing Sempurna**:
   * Mempertahankan transparansi penuh frame PNG (mode `RGBA`).
   * Menjamin lapisan frame selalu berada di lapisan teratas (*overlay*), sehingga ornamen bingkai menutupi tepian foto secara rapi.
6. **Keamanan File Sumber (Strict Non-Destructive)**:
   * File foto asli milik pengguna **tidak pernah diubah atau ditimpa** (terbukti dengan verifikasi checksum SHA-256 identik).
   * File hasil disimpan ke folder output terpisah dengan fitur pencegahan penimpaan file (*collision-safe* otomatis `_1`, `_2`).
   * Penulisan file *atomic* (`.tmp_...` $\rightarrow$ replace) untuk mencegah file korup jika terjadi interupsi.
7. **Responsivitas Antarmuka & Toleransi Kegagalan**:
   * Pemrosesan batch berjalan di *background worker thread* terpisah (`threading.Thread`), menjaga GUI tetap responsif tanpa *freeze*.
   * Sinyal pembatalan instan (*graceful cancellation*) yang langsung menghentikan proses dan membersihkan file sementara.
   * File foto yang rusak tidak menghentikan keseluruhan batch (*fault-tolerant*).
8. **Pelaporan & Persistensi Konfigurasi**:
   * Otomatis mengekspor ringkasan eksekusi ke file `processing_report.json` dan `processing_report.csv`.
   * Konfigurasi folder, frame, dan koordinat slot otomatis tersimpan di `user_config.json` dan langsung dimuat saat aplikasi dibuka kembali.

---

## 📂 Struktur Direktori Proyek

```text
PhotoFrameProcessor/
├── assets/
│   └── borders/                  # Template frame PNG transparan
│       ├── demo/                 # Frame demo bawaan untuk pengujian & repositori publik
│       │   ├── demo_frame_a.png  # Frame demo Desain A (1200x1200 px)
│       │   └── demo_frame_b.png  # Frame demo Desain B (1400x1000 px)
│       └── final/                # Frame final tim dokumentasi (lokal, di-ignore Git)
│           ├── frame_desain_a.png
│           └── frame_desain_b.png
├── src/
│   ├── config/                   # Pengaturan konstanta, data model Pydantic, & persistensi
│   │   ├── settings.py
│   │   ├── models.py
│   │   └── persistence.py
│   ├── core/                     # Core Image Processing Engine (Pillow RGBA)
│   │   ├── validator.py
│   │   ├── exif_handler.py
│   │   ├── transform.py
│   │   ├── compositor.py
│   │   ├── hole_detector.py
│   │   ├── writer.py
│   │   └── processor.py
│   ├── pipeline/                 # Pipeline batch runner, scanner, & pelaporan
│   │   ├── scanner.py
│   │   ├── reporter.py
│   │   └── runner.py
│   └── gui/                      # Desktop GUI CustomTkinter
│       ├── app.py                # Jendela utama aplikasi
│       ├── components/           # Widget modular (placement editor, batch card, progress)
│       │   ├── placement_editor.py
│       │   ├── batch_card.py
│       │   ├── preview_modal.py
│       │   ├── progress_panel.py
│       │   └── log_console.py
│       └── controllers/          # Thread dispatcher & logika kontrol
│           └── main_controller.py
├── tests/                        # Test suite otomatis (pytest)
│   ├── conftest.py
│   ├── unit/                     # Unit test core engine & komponen GUI (29 tests)
│   │   ├── test_core_engine.py
│   │   └── test_gui_components.py
│   ├── integration/              # Integration test batch pipeline (9 tests)
│   │   └── test_batch_pipeline.py
│   ├── performance/              # Benchmark beban 500 foto
│   │   └── test_benchmark_500.py
│   └── manual_verification.py    # Skrip verifikasi alur kerja manual otomatis
├── PhotoFrameProcessor.spec      # Konfigurasi packaging PyInstaller
├── requirements.txt              # Daftar dependensi Python
├── main.py                       # Titik masuk eksekusi aplikasi
└── README.md                     # Dokumentasi panduan penggunaan
```

---

## 💻 Persyaratan Sistem

* **Sistem Operasi**: Windows 10 / Windows 11 (64-bit).
* **Python Runtime**: Python 3.10 hingga Python 3.13 (Disarankan Python 3.13).
* **Memori (RAM)**: Minimal 4 GB (Penggunaan RAM aplikasi sangat efisien, stabil di ~75 MB).

---

## 🚀 Instalasi & Persiapan

1. **Buka Terminal / PowerShell** di direktori proyek ini:
   ```bash
   cd c:\xampp\htdocs\ProcecingFoto
   ```

2. **Instal Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Cara Menjalankan Aplikasi

Jalankan perintah berikut pada terminal:

```bash
python main.py
```

Antarmuka desktop **PhotoFrameProcessor** akan langsung terbuka.

---

## 📖 Panduan Penggunaan Langkah demi Langkah

### 1. Menyiapkan Batch 1 dan Batch 2
1. Pada kartu **Pengaturan Batch 1**:
   * Klik tombol **Pilih Folder** untuk memilih folder berisi foto-foto pertama (maksimal 250 foto).
   * Klik tombol **Pilih Frame** untuk memilih file template frame PNG transparan (aplikasi otomatis mendeteksi prioritas: `assets/borders/final/frame_desain_a.png` jika ada di komputer lokal, atau frame demo `assets/borders/demo/demo_frame_a.png`).
2. Pada kartu **Pengaturan Batch 2**:
   * Lakukan langkah yang sama untuk batch kedua (prioritas: `assets/borders/final/frame_desain_b.png` atau frame demo `assets/borders/demo/demo_frame_b.png`).
3. Label informasi akan otomatis menampilkan jumlah foto yang valid dan resolusi dimensi frame PNG.

> [!NOTE]
> **Hierarki Resolusi Frame Default:**
> Sistem secara otomatis menggunakan urutan resolusi berikut:
> 1. **Final Frame** (`assets/borders/final/` - aset spesifik acara lokal, diabaikan oleh Git).
> 2. **Demo Frame** (`assets/borders/demo/` - aset terbuka yang disertakan dalam repositori Git).
> 3. **None** (jika keduanya belum tersedia, pengguna dapat memilih frame sendiri via tombol dialog).

### 2. Mengatur Area Foto dengan Photo Placement Editor
1. Klik tombol **Atur Area Foto (Editor)** pada kartu batch yang diinginkan.
2. Jendela **Interactive Photo Placement Editor** akan terbuka:
   * **Deteksi Lubang Otomatis**: Klik tombol hijau *"Deteksi Lubang Otomatis"* untuk membiarkan sistem memindai saluran alpha transparan frame secara instan.
   * **Atur Manual**: Klik dan geser kotak garis putus-putus (*drag bounding box*) untuk memindahkan posisi, atau drag di luar kotak untuk membuat area baru.
   * **Input Presisi**: Masukkan koordinat numerik **X**, **Y**, **Lebar**, dan **Tinggi** pada panel kanan, lalu klik *"Terapkan Koordinat"*.
   * **Ganti Orientasi Sampel**: Klik tombol *"Ganti Orientasi Sampel (P/L)"* untuk melihat simulasi tampilan foto portrait vs landscape di balik frame.
3. Klik tombol **Simpan Koordinat** untuk menyimpan pengaturan.

### 3. Melihat Preview Hasil
* Klik tombol **Lihat Preview** pada kartu batch untuk melihat simulasi hasil komposit sebelum proses batch dimulai.
* Anda dapat beralih antara *"Sampel Portrait"* dan *"Sampel Landscape"* untuk memastikan tidak ada bagian penting foto yang terpotong.

### 4. Menentukan Folder Output & Menjalankan Proses
1. Pada panel bawah, periksa jalur **Folder Output Hasil** (secara default di folder `outputs/`). Klik *Pilih Folder* jika ingin mengubah lokasi.
2. Klik tombol hijau besar **Mulai Proses 500 Foto**.
3. Pantau progres secara langsung:
   * **Progress Bar & Persentase**: Menampilkan laju penyelesaian keseluruhan.
   * **Counter Real-time**: Menampilkan jumlah foto sukses dan gagal.
   * **Estimasi Waktu (ETA)**: Menghitung perkiraan sisa waktu pemrosesan secara dinamis.
   * **Konsol Log**: Menampilkan riwayat status per file.
4. Jika ingin menghentikan proses di tengah jalan, klik tombol merah **Batal**. Proses akan berhenti dengan aman tanpa meninggalkan file sementara yang rusak.

### 5. Membuka Hasil & Membaca Laporan
1. Setelah selesai, klik tombol **Buka Folder Hasil** untuk membuka Windows Explorer langsung ke folder output.
2. Hasil foto tersimpan di subdirektori terorganisir:
   * `outputs/batch_frame_1/` : Hasil pemrosesan Batch 1.
   * `outputs/batch_frame_2/` : Hasil pemrosesan Batch 2.
3. Di dalam folder output juga tersedia dua file laporan:
   * **`processing_report.json`**: Laporan statistik lengkap dalam format JSON yang memuat total durasi, rata-rata durasi per foto, *throughput* (foto/detik), serta daftar kegagalan jika ada.
   * **`processing_report.csv`**: Rincian status tabel per-file foto (Nama File, Path Sumber, Path Output, Status SUCCESS/FAILED, Waktu Eksekusi dalam milidetik, dan Pesan Error).

---

## 🧪 Menjalankan Pengujian Otomatis

Aplikasi ini dilengkapi dengan suite pengujian otomatis berbasis `pytest`:

```bash
# Menjalankan seluruh 38 unit & integration test
pytest tests/unit/ tests/integration/ -v

# Menjalankan uji beban benchmark 500 foto
pytest tests/performance/test_benchmark_500.py -v -s

# Menjalankan verifikasi alur kerja manual otomatis
python tests/manual_verification.py
```

---

## 🔧 Troubleshooting & Tanya Jawab

* **T: Mengapa foto saya tampak terpotong?**
  * *J*: Aplikasi menggunakan prinsip *Aspect Fill / Cover* untuk menjamin seluruh area slot foto terisi penuh tanpa meninggalkan ruang kosong atau mendistorsi rasio aspek foto. Gunakan *Photo Placement Editor* untuk memperbesar atau menyesuaikan area slot foto pada frame Anda.
* **T: Apakah file foto asli saya aman?**
  * *J*: **100% aman.** Seluruh file input dibuka dalam mode *read-only*. Hasil selalu disimpan ke folder baru dan tidak akan menimpa file yang sudah ada (secara otomatis ditambahkan sufiks `_1`, `_2`).
* **T: Format citra apa saja yang didukung?**
  * *J*: Foto sumber mendukung format `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, dan `.tiff`. Template frame harus berformat `.png` transparan.
* **T: Bagaimana cara mengembalikan konfigurasi default?**
  * *J*: Cukup hapus file `user_config.json` di folder utama aplikasi. Saat aplikasi dibuka kembali, pengaturan default akan dimuat ulang.
