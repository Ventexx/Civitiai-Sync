"""
Civitai Sync - A lightweight CLI tool that synchronizes safetensor model metadata
and preview images from Civitai into a local directory.
"""

__version__ = "1.5.0"
__author__ = "Ventexx"
__description__ = (
    "A lightweight CLI tool that synchronizes safetensor model metadata "
    "and preview images from Civitai into a local directory."
)

from .civitai_api import CivitaiAPIClient
from .civitai_processor import CivitaiProcessor, process_civitai_directory
from .config_manager import ConfigManager
from .file_manager import FileManager
from .hash_utils import compute_sha256, verify_safetensor_file

__all__ = [
    "CivitaiProcessor",
    "process_civitai_directory",
    "CivitaiAPIClient",
    "FileManager",
    "ConfigManager",
    "compute_sha256",
    "verify_safetensor_file",
]
