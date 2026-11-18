"""
Core image transformation and compositing engine package.
"""

from src.core.validator import (
    validate_photo_path,
    validate_frame_path,
    load_photo_image,
    load_frame_image,
    ImageValidationError,
)
from src.core.exif_handler import normalize_exif_orientation, get_exif_orientation
from src.core.transform import resize_and_center_crop
from src.core.compositor import compose_frame_with_photo, validate_slot_within_frame, SlotOutOfBoundsError
from src.core.writer import save_image_safely, get_unique_filepath
from src.core.processor import process_single_photo

__all__ = [
    "validate_photo_path",
    "validate_frame_path",
    "load_photo_image",
    "load_frame_image",
    "ImageValidationError",
    "normalize_exif_orientation",
    "get_exif_orientation",
    "resize_and_center_crop",
    "compose_frame_with_photo",
    "validate_slot_within_frame",
    "SlotOutOfBoundsError",
    "save_image_safely",
    "get_unique_filepath",
    "process_single_photo",
]
