
## `main.py`

The CLI entrypoint.

 - **`setup_logging(verbose: bool = False)`**: Configures Python’s `logging` module (INFO vs DEBUG).
 - **`save_api_key(api_key: str) -> bool`**: Delegates to `ConfigManager` to persist an API key.
 - **`main() -> int`**:

  1. Parses CLI arguments (folder path, API key options, flags).
  2. Handles `--save-api-key` (writes config and exits).
  3. Validates the target folder.
  4. Reads the API key (either from flag or config).
  5. Instantiates `CivitaiProcessor` and calls `process_directory()`.
  6. Catches and reports errors or keyboard interrupts.
 - At the bottom, runs `sys.exit(main())` when invoked as a script.

---

## `setup.py`

Packaging and installation configuration.

 - Defines package name, version, dependencies (via `requirements.txt`), and supported Python versions.
 - Registers `civitai-sync` as a console script pointing to `main:main`.
 - Includes `py_modules=['main']` so that `main.py` is installed as a top-level module.

---

## `src/__init__.py`

Package manifest — exposes key symbols at the package level:

 - `CivitaiProcessor`, `process_civitai_directory`
 - `CivitaiAPIClient`
 - `FileManager`, `ConfigManager`
 - `compute_sha256`, `verify_safetensor_file`

---

## `src/config_manager.py`

Handles persistent storage of user settings (currently just the API key).

 - **`ConfigManager`**:

   - Creates a `~/.civitai-sync` directory and `config.json`.
   - **`save_api_key(key: str) -> bool`**, **`get_api_key() -> Optional[str]`**, **`remove_api_key() -> bool`**: CRUD operations for the API key.
   - **`get_setting(key: str, default: Any) -> Any`**, **`set_setting(key: str, value: Any) -> bool`**: Generic config accessors.

---

## `src/civitai_api.py`

Thin wrapper over the Civitai REST API with rate-limiting and retries.

 - **`CivitaiAPIClient`**:

   - Manages an authenticated `requests.Session`.
   - **`_wait_for_rate_limit()`**, **`_exponential_backoff(attempt, base_delay, max_delay)`**, **`_make_request_with_retry(url, max_retries)`**: Helpers for polite, resilient HTTP calls.
   - **`get_model_by_hash(sha256_hash: str) -> Optional[Dict]`**: Fetches model metadata via SHA256 lookup.
   - **`get_image_urls_from_metadata(metadata: Dict) -> List[str]`**, **`get_primary_image_url(metadata: Dict) -> Optional[str]`**: Extract preview URLs from the API response.
   - **`download_image(image_url: str, output_path: Path) -> bool`**: Streams an image from the web to disk.

---

## `src/file_manager.py`

Abstracts all filesystem operations around `.safetensor`, `.json`, and `.preview.png` files.

 - **`FileManager(folder_path: str)`**: Constructor validates the directory.
 - **`find_safetensor_files() -> List[Path]`**: Recursively globs for `.safetensor(s)` files.
 - **`get_json_path(safetensor_path: Path) -> Path`**, **`get_preview_path(safetensor_path: Path) -> Path`**: Compute companion file paths.
 - **`load_existing_json(json_path: Path) -> Optional[Dict]`**, **`save_json(json_path: Path, data: Dict) -> bool`**: Read/write JSON with error handling.
 - **`get_sha256_from_json(json_data: Dict) -> Optional[str]`**: Heuristically extract a hex hash from JSON.
 - **`analyze_directory() -> Tuple[List[Path], List[Path]]`**: Splits files into those needing hashing vs. those that don’t.
 - **`get_all_hashes() -> Dict[str, str]`**: Builds a map of `filepath -> hash` from existing JSON.
 - **`cleanup_orphaned_files() -> Dict[str, int]`**: Deletes JSON or preview files whose safetensor files no longer exist.

---

## `src/hash_utils.py`

Low-level safetensor file inspection and SHA256 computation.

 - **`compute_sha256(file_path: Union[str, Path], chunk_size: int, quiet: bool) -> str`**: Streams the file in chunks to build a SHA256 digest, logging progress for large files.
 - **`verify_safetensor_file(file_path: Union[str, Path]) -> bool`**:

   - Checks extension, non-zero length, and reads the 8-byte header length + JSON header to confirm it matches the safetensor format.
 - **`get_safetensor_metadata(file_path: Union[str, Path]) -> Dict`**: Extracts the JSON header’s `__metadata__` field and reports additional info (file size, tensor count).
 - **`validate_sha256_hash(hash_string: str) -> bool`**: Ensures a string is 64 hex characters.

---

## `src/progress_handler.py`

Terminal feedback utilities.

 - **`ProgressBar(total: int, description: str, width: int)`**:

   - Draws an ASCII progress bar, throttles redraws, and prints ETA.
   - Methods: **`update(current: int, description?: str)`**, **`finish(description?: str)`**.
 - **`StatusDisplay`**: Static methods for printing styled messages:

   - **`print_header(message: str)`**, **`print_success(message: str)`**, **`print_warning(message: str)`**, **`print_error(message: str)`**, **`print_info(message: str)`**, **`print_results(stats: dict)`** (summarizes final stats).

