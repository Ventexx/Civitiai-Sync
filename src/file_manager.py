"""
Enhanced file management utilities for handling safetensor and JSON files
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class FileManager:
    """Enhanced manager for safetensor and JSON files in a directory"""
    
    def __init__(self, folder_path: str):
        """
        Initialize FileManager
        
        Args:
            folder_path: Path to the folder containing safetensor files
        """
        self.folder_path = Path(folder_path)
        if not self.folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        if not self.folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")
    
    def find_safetensor_files(self) -> List[Path]:
        """
        Find all safetensor files in the directory
        
        Returns:
            List of Path objects for safetensor files
        """
        safetensor_files = []
        
        # Look for both .safetensors and .safetensor extensions
        for pattern in ['*.safetensors', '*.safetensor']:
            safetensor_files.extend(self.folder_path.glob(pattern))
        
        # Also search recursively in subdirectories
        for pattern in ['**/*.safetensors', '**/*.safetensor']:
            safetensor_files.extend(self.folder_path.glob(pattern))
        
        # Remove duplicates and sort
        safetensor_files = sorted(list(set(safetensor_files)))
        
        logger.info(f"Found {len(safetensor_files)} safetensor files in {self.folder_path}")
        
        if not safetensor_files:
            logger.warning(f"No safetensor files found in {self.folder_path}")
        
        return safetensor_files
    
    def get_json_path(self, safetensor_path: Path) -> Path:
        """
        Get the corresponding JSON file path for a safetensor file
        
        Args:
            safetensor_path: Path to the safetensor file
            
        Returns:
            Path to the corresponding JSON file
        """
        return safetensor_path.with_suffix('.json')
    
    def get_preview_path(self, safetensor_path: Path) -> Path:
        """
        Get the corresponding preview image path for a safetensor file
        
        Args:
            safetensor_path: Path to the safetensor file
            
        Returns:
            Path to the corresponding preview image file
        """
        return safetensor_path.with_suffix('.preview.png')
    
    def load_existing_json(self, json_path: Path) -> Optional[Dict[Any, Any]]:
        """
        Load existing JSON file if it exists
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            Dictionary containing JSON data, or None if file doesn't exist or is invalid
        """
        if not json_path.exists():
            return None
        
        try:
            with json_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Loaded existing JSON: {json_path.name}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load JSON file {json_path}: {e}")
            return None
    
    def save_json(self, json_path: Path, data: Dict[Any, Any]) -> bool:
        """
        Save data to JSON file with proper formatting
        
        Args:
            json_path: Path to the JSON file
            data: Data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with json_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
            logger.debug(f"Saved JSON: {json_path.name}")
            return True
        except IOError as e:
            logger.error(f"Could not save JSON file {json_path}: {e}")
            return False
    
    def get_sha256_from_json(self, json_data: Dict[Any, Any]) -> Optional[str]:
        """
        Extract SHA256 hash from JSON data
        
        Args:
            json_data: Dictionary containing JSON data
            
        Returns:
            SHA256 hash if found, None otherwise
        """
        # Look for sha256 in various possible locations
        possible_keys = ['sha256', 'SHA256', 'hash', 'computed_hash']
        
        for key in possible_keys:
            if key in json_data and json_data[key]:
                hash_value = str(json_data[key]).lower()
                # Basic validation - SHA256 should be 64 hex characters
                if len(hash_value) == 64 and all(c in '0123456789abcdef' for c in hash_value):
                    return hash_value
        
        return None
    
    def analyze_directory(self) -> Tuple[List[Path], List[Path]]:
        """
        Analyze directory to find which files need hash computation
        
        Returns:
            Tuple of (files_needing_hash, files_with_existing_hash)
        """
        safetensor_files = self.find_safetensor_files()
        files_needing_hash = []
        files_with_existing_hash = []
        
        for safetensor_file in safetensor_files:
            json_path = self.get_json_path(safetensor_file)
            existing_json = self.load_existing_json(json_path)
            
            if existing_json and self.get_sha256_from_json(existing_json):
                files_with_existing_hash.append(safetensor_file)
                logger.debug(f"Hash exists for: {safetensor_file.name}")
            else:
                files_needing_hash.append(safetensor_file)
                logger.debug(f"Hash needed for: {safetensor_file.name}")
        
        logger.info(f"Analysis complete: {len(files_needing_hash)} need hashing, "
                   f"{len(files_with_existing_hash)} already have hashes")
        
        return files_needing_hash, files_with_existing_hash
    
    def get_all_hashes(self) -> Dict[str, str]:
        """
        Get all existing hashes from JSON files
        
        Returns:
            Dictionary mapping file paths to their SHA256 hashes
        """
        hashes = {}
        safetensor_files = self.find_safetensor_files()
        
        for safetensor_file in safetensor_files:
            json_path = self.get_json_path(safetensor_file)
            existing_json = self.load_existing_json(json_path)
            
            if existing_json:
                hash_value = self.get_sha256_from_json(existing_json)
                if hash_value:
                    hashes[str(safetensor_file)] = hash_value
        
        return hashes
    
    def cleanup_orphaned_files(self) -> Dict[str, int]:
        """
        Clean up JSON and preview files that don't have corresponding safetensor files
        
        Returns:
            Dictionary with counts of cleaned files
        """
        safetensor_files = set(self.find_safetensor_files())
        
        # Find all JSON and preview files
        json_files = list(self.folder_path.glob('*.json')) + list(self.folder_path.glob('**/*.json'))
        preview_files = list(self.folder_path.glob('*.preview.png')) + list(self.folder_path.glob('**/*.preview.png'))
        
        cleaned_json = 0
        cleaned_previews = 0
        
        # Check JSON files
        for json_file in json_files:
            # Find corresponding safetensor file
            safetensor_file = json_file.with_suffix('.safetensors')
            if not safetensor_file.exists():
                safetensor_file = json_file.with_suffix('.safetensor')
            
            if safetensor_file not in safetensor_files:
                try:
                    json_file.unlink()
                    cleaned_json += 1
                    logger.info(f"Removed orphaned JSON: {json_file.name}")
                except Exception as e:
                    logger.error(f"Failed to remove {json_file}: {e}")
        
        # Check preview files
        for preview_file in preview_files:
            # Find corresponding safetensor file
            base_name = preview_file.name.replace('.preview.png', '')
            safetensor_file = preview_file.parent / f"{base_name}.safetensors"
            if not safetensor_file.exists():
                safetensor_file = preview_file.parent / f"{base_name}.safetensor"
            
            if safetensor_file not in safetensor_files:
                try:
                    preview_file.unlink()
                    cleaned_previews += 1
                    logger.info(f"Removed orphaned preview: {preview_file.name}")
                except Exception as e:
                    logger.error(f"Failed to remove {preview_file}: {e}")
        
        return {
            'json_files_cleaned': cleaned_json,
            'preview_files_cleaned': cleaned_previews
        }