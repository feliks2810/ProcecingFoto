"""
Konsol log teks scrolling real-time dan area laporan pemrosesan.
"""

from datetime import datetime
import customtkinter as ctk


class LogConsole(ctk.CTkFrame):
    """
    Komponen kotak teks log scrolling untuk menampilkan progres real-time
    dan laporan akhir proses framing foto.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=10, pady=(6, 4), sticky="ew")

        lbl_title = ctk.CTkLabel(
            header,
            text="Riwayat & Laporan Pemrosesan",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        lbl_title.pack(side="left")

        btn_clear = ctk.CTkButton(
            header,
            text="Bersihkan Log",
            width=90,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#424242",
            hover_color="#303030",
            command=self.clear
        )
        btn_clear.pack(side="right")

        # Textbox Log
        self.textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def log(self, message: str) -> None:
        """Menambahkan satu baris log dengan timestamp."""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"
        self.textbox.insert("end", line)
        self.textbox.see("end")

    def clear(self) -> None:
        """Membersihkan seluruh isi log."""
        self.textbox.delete("1.0", "end")
