"""
Configuration and data models package.
"""

from src.config.settings import (
    APP_NAME,
    APP_VERSION,
    APP_TITLE,
    BASE_DIR,
    ASSETS_DIR,
    BORDERS_DIR,
    DEMO_BORDERS_DIR,
    FINAL_BORDERS_DIR,
    SUPPORTED_PHOTO_EXTENSIONS,
    SUPPORTED_FRAME_EXTENSIONS,
    DEFAULT_PHOTOS_PER_BATCH,
    MAX_RECOMMENDED_TOTAL_PHOTOS,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_SUBFOLDER_BATCH_1,
    DEFAULT_SUBFOLDER_BATCH_2,
)
from src.config.models import (
    SlotCoordinates,
    SingleBatchConfig,
    BatchConfig,
    FileResult,
    BatchSummaryReport,
)
from src.config.persistence import (
    save_user_config,
    load_user_config,
    DEFAULT_USER_CONFIG_PATH,
)

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "APP_TITLE",
    "BASE_DIR",
    "ASSETS_DIR",
    "BORDERS_DIR",
    "DEMO_BORDERS_DIR",
    "FINAL_BORDERS_DIR",
    "SUPPORTED_PHOTO_EXTENSIONS",
    "SUPPORTED_FRAME_EXTENSIONS",
    "DEFAULT_PHOTOS_PER_BATCH",
    "MAX_RECOMMENDED_TOTAL_PHOTOS",
    "DEFAULT_OUTPUT_FORMAT",
    "DEFAULT_OUTPUT_QUALITY",
    "DEFAULT_SUBFOLDER_BATCH_1",
    "DEFAULT_SUBFOLDER_BATCH_2",
    "SlotCoordinates",
    "SingleBatchConfig",
    "BatchConfig",
    "FileResult",
    "BatchSummaryReport",
    "save_user_config",
    "load_user_config",
    "DEFAULT_USER_CONFIG_PATH",
]
