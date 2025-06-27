import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manages safetensor discovery and basic JSON loading operations.
    """
    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)
        if not self.folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        if not self.folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")

    def find_safetensor_files(self) -> List[Path]:
        """
        Recursively find all .safetensors and .safetensor files.
        """
        patterns = ['**/*.safetensors', '**/*.safetensor']
        files = []
        for pattern in patterns:
            files.extend(self.folder_path.glob(pattern))
        unique_files = sorted(set(files))
        logger.info(f"Found {len(unique_files)} safetensor file(s) in {self.folder_path}")
        return unique_files

    def get_json_path(self, safetensor_path: Path) -> Path:
        """Return the .json sibling path for a safetensor file."""
        return safetensor_path.with_suffix('.json')

    def get_preview_path(self, safetensor_path: Path) -> Path:
        """Return the .preview.png sibling path for a safetensor file."""
        return safetensor_path.with_suffix('.preview.png')

    def load_existing_json(self, json_path: Path) -> Optional[Dict[Any, Any]]:
        """
        Safely load a JSON file if it exists, otherwise return None.
        """
        if not json_path.exists():
            return None
        try:
            return json.loads(json_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed loading JSON {json_path.name}: {e}")
            return None

    def get_sha256_from_json(self, json_data: Dict[Any, Any]) -> Optional[str]:
        """
        Extract a valid SHA256 string from known keys in JSON.
        """
        for key in ('sha256', 'SHA256', 'hash', 'computed_hash'):
            val = json_data.get(key)
            if isinstance(val, str):
                h = val.strip().lower()
                if len(h) == 64 and all(c in '0123456789abcdef' for c in h):
                    return h
        return None

    def analyze_directory(self) -> Tuple[List[Path], List[Path]]:
        """
        Determine which safetensor files need hashing based on existing JSON.

        Returns:
            (files_needing_hash, files_with_hash)
        """
        safetensors = self.find_safetensor_files()
        need, have = [], []
        for st in safetensors:
            jpath = self.get_json_path(st)
            data = self.load_existing_json(jpath)
            if data and self.get_sha256_from_json(data):
                have.append(st)
            else:
                need.append(st)
        logger.info(f"Directory analysis: {len(need)} need hashing, {len(have)} have hashes")
        return need, have

    def get_all_hashes(self) -> Dict[str, str]:
        """
        Return a mapping of safetensor paths to their stored SHA256 hashes.
        """
        hashes: Dict[str, str] = {}
        for st in self.find_safetensor_files():
            data = self.load_existing_json(self.get_json_path(st))
            if data:
                h = self.get_sha256_from_json(data)
                if h:
                    hashes[str(st)] = h
        return hashes

    def cleanup_orphaned_files(self) -> Dict[str, int]:
        """
        Remove JSON and preview files without corresponding safetensor.

        Returns counts of cleaned JSON and preview files.
        """
        safetensors = {p.resolve() for p in self.find_safetensor_files()}
        jsons = list(self.folder_path.rglob('*.json'))
        previews = list(self.folder_path.rglob('*.preview.png'))
        cleaned = {'json': 0, 'preview': 0}

        for f in jsons:
            st = f.with_suffix('.safetensors').resolve()
            if not st.exists():
                f.unlink(missing_ok=True)
                cleaned['json'] += 1
        for f in previews:
            st = f.with_suffix('.safetensor').resolve()
            if not st.exists():
                f.unlink(missing_ok=True)
                cleaned['preview'] += 1

        logger.info(f"Cleaned {cleaned['json']} JSON and {cleaned['preview']} preview files")
        return {'json_files_cleaned': cleaned['json'], 'preview_files_cleaned': cleaned['preview']}
