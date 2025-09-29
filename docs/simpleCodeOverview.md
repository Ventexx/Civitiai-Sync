# Overview

## __init__.py
Package initialization file that defines the module version, author info, and exports the main classes and functions for easy importing.

## civitai_api.py
API client for communicating with Civitai's web service, handling HTTP requests with retry logic, rate limiting, exponential backoff, and downloading model metadata and preview images.

## civitai_processor.py
Main orchestration layer that coordinates the entire sync workflow: validates safetensor files, computes hashes, fetches metadata from Civitai, saves JSON files, and downloads images.

## config_manager.py
Manages persistent configuration storage (like API keys) in the user's home directory, providing simple load/save operations for settings.

## file_manager.py
Handles all file system operations including discovering safetensor files, managing JSON/preview file paths, loading existing metadata, and cleaning up orphaned files.

## hash_utils.py
Provides SHA256 hash computation for safetensor files with progress tracking, plus validation functions to verify file integrity and structure.

## main.py
Command-line interface entry point that parses arguments, sets up logging, and invokes the processor with user-specified options.

## metadata_saver.py
Legacy helper class for saving metadata (functionality now mostly moved to civitai_processor.py), retained primarily for backwards compatibility.

## progress_handler.py
Terminal UI components including progress bars with ETA calculations and formatted status messages with timestamps and elapsed time tracking.
