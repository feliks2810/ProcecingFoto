"""
Titik masuk utama (entry point) aplikasi desktop PhotoFrameProcessor.
"""

import sys
import logging
from src.config.settings import APP_NAME, APP_VERSION, LOG_DATE_FORMAT, LOG_FORMAT
from src.gui.app import PhotoFrameProcessorApp

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Menginisialisasi dan menjalankan aplikasi GUI desktop."""
    logger.info("Memulai %s v%s...", APP_NAME, APP_VERSION)
    try:
        app = PhotoFrameProcessorApp()
        app.mainloop()
    except Exception as exc:
        logger.critical("Aplikasi mengalami fatal crash: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
