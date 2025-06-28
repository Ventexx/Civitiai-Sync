"""
Enhanced processor for handling Civitai API integration with local safetensor files
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import OrderedDict
import json

from .civitai_api import CivitaiAPIClient
from .file_manager import FileManager
from .hash_utils import compute_sha256, verify_safetensor_file
from .progress_handler import StatusDisplay

logger = logging.getLogger(__name__)


class CivitaiProcessor:
    """Enhanced processor for Civitai integration"""
    
    def __init__(self, folder_path: str, api_key: Optional[str] = None, 
                 rate_limit_delay: float = 1.0, refresh_metadata: bool = False,
                 max_metadata_age_days: int = 30):
        """
        Initialize CivitaiProcessor
        
        Args:
            folder_path: Path to folder containing safetensor files
            api_key: Optional Civitai API key
            rate_limit_delay: Delay between API requests in seconds
            refresh_metadata: Force refresh of all metadata
            max_metadata_age_days: Maximum age of metadata before refresh
        """
        self.file_manager = FileManager(folder_path)
        self.api_client = CivitaiAPIClient(api_key, rate_limit_delay)
        self.folder_path = Path(folder_path)
        self.refresh_metadata = refresh_metadata
        self.max_metadata_age_days = max_metadata_age_days
    
    def validate_safetensor_files(self, files: List[Path]) -> List[Path]:
        """
        Validate that files are proper safetensor files
        
        Args:
            files: List of file paths to validate
            
        Returns:
            List of valid safetensor files
        """
        valid_files = []
        
        for file_path in files:
            if verify_safetensor_file(file_path):
                valid_files.append(file_path)
            else:
                logger.warning(f"Invalid or corrupted safetensor file: {file_path.name}")
        
        if files and not valid_files:
            # All files failed validation
            logger.error("All safetensor files are invalid or corrupted; aborting.")
            raise ValueError("No valid safetensor files found")

        return valid_files
    
    def compute_missing_hashes(self, files_needing_hash: List[Path]) -> Dict[Path, str]:
        """
        Compute SHA256 hashes for files that don't have them
        
        Args:
            files_needing_hash: List of files that need hash computation
            
        Returns:
            Dictionary mapping file paths to their computed hashes
        """
        from .progress_handler import ProgressBar
        
        computed_hashes = {}
        
        # Validate files first
        valid_files = self.validate_safetensor_files(files_needing_hash)
        
        if len(valid_files) != len(files_needing_hash):
            logger.warning(f"Skipping {len(files_needing_hash) - len(valid_files)} invalid files")
        
        if not valid_files:
            return computed_hashes
        
        # Create progress bar for hash computation
        progress = ProgressBar(len(valid_files), "Computing SHA256 hashes...")
        
        for i, file_path in enumerate(valid_files):
            try:
                hash_value = compute_sha256(file_path, quiet=True)
                computed_hashes[file_path] = hash_value
                progress.update(i + 1)
            except Exception as e:
                logger.error(f"Failed to compute hash for {file_path.name}: {e}")
                progress.update(i + 1)
        
        progress.finish("Hash computation completed")
        return computed_hashes
    
    def is_metadata_stale(self, json_data: Dict[Any, Any]) -> bool:
        """
        Check if metadata is stale and needs refreshing
        
        Args:
            json_data: Existing JSON data
            
        Returns:
            True if metadata should be refreshed
        """
        if self.refresh_metadata:
            return True
        
        # Check if we have the required metadata fields
        required_fields = ['model', 'modelId', 'modelVersionId']
        if not all(field in json_data for field in required_fields):
            return True
        
        # Check last update timestamp
        if 'last_updated' in json_data:
            try:
                last_updated = datetime.fromisoformat(json_data['last_updated'])
                max_age = timedelta(days=self.max_metadata_age_days)
                return datetime.now() - last_updated > max_age
            except (ValueError, TypeError):
                return True
        
        return True  # No timestamp, consider stale
    
    def analyze_metadata_freshness(self) -> tuple[List[Path], List[Path]]:
        """
        Analyze which files need metadata refresh
        
        Returns:
            Tuple of (files_needing_metadata, files_with_fresh_metadata)
        """
        safetensor_files = self.file_manager.find_safetensor_files()
        files_needing_metadata = []
        files_with_fresh_metadata = []
        
        for safetensor_file in safetensor_files:
            json_path = self.file_manager.get_json_path(safetensor_file)
            existing_json = self.file_manager.load_existing_json(json_path)
            
            if not existing_json or self.is_metadata_stale(existing_json):
                files_needing_metadata.append(safetensor_file)
            else:
                files_with_fresh_metadata.append(safetensor_file)
        
        logger.info(f"Metadata analysis: {len(files_needing_metadata)} need refresh, "
                   f"{len(files_with_fresh_metadata)} are fresh")
        
        return files_needing_metadata, files_with_fresh_metadata
    
    def fetch_and_save_metadata(self, file_hash_map: Dict[Path, str]) -> Dict[str, Any]:
        """
        Fetch metadata from Civitai and save it in the specified format
        
        Args:
            file_hash_map: Dictionary mapping file paths to their hashes
            
        Returns:
            Dictionary with processing statistics
        """
        from .progress_handler import ProgressBar
        
        stats = {
            'metadata_fetched': 0,
            'files_saved': 0,
            'not_found': 0,
            'errors': []
        }
        
        if not file_hash_map:
            return stats
        
        # Create progress bar for API calls
        progress = ProgressBar(len(file_hash_map), "Fetching and saving metadata...")
        
        for i, (file_path, hash_value) in enumerate(file_hash_map.items(), 1):
            try:
                # Fetch metadata from Civitai
                metadata = self.api_client.get_model_by_hash(hash_value)
                
                if metadata:
                    stats['metadata_fetched'] += 1
                    
                    # Save metadata in the specified format
                    if self.save_metadata_file(file_path, hash_value, metadata):
                        stats['files_saved'] += 1
                    else:
                        stats['errors'].append(f"Failed to save metadata for {file_path.name}")
                else:
                    stats['not_found'] += 1
                    # Save minimal JSON with just hash and not found flag
                    self.save_minimal_metadata(file_path, hash_value)
                
                progress.update(i)
                    
            except Exception as e:
                error_msg = f"Error processing {file_path.name}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                progress.update(i)
        
        progress.finish(f"Processing completed - {stats['metadata_fetched']} models found")
        
        return stats

    def save_metadata_file(self, file_path: Path, sha256_hash: str, metadata: Dict[Any, Any]) -> bool:
        """
        Save metadata to JSON file in the specified format and order
        
        Args:
            file_path: Path to the safetensor file
            sha256_hash: SHA256 hash of the file
            metadata: Raw metadata from Civitai API
            
        Returns:
            True if saved successfully, False otherwise
        """
        json_path = self.file_manager.get_json_path(file_path)
        
        try:
            # Create ordered dictionary with specified structure and order
            json_data = OrderedDict()
            
            # 1. SHA256 hash (always first)
            json_data['sha256'] = sha256_hash
            
            # 2. Model info (extract from metadata structure)
            model_info = OrderedDict()
            
            # The model info might be nested in different ways depending on the API response
            model_data = None
            if 'model' in metadata and isinstance(metadata['model'], dict):
                model_data = metadata['model']
            elif isinstance(metadata, dict):
                # Sometimes the model info is at the top level
                model_data = metadata
            
            if model_data:
                model_info['name'] = model_data.get('name', '')
                model_info['type'] = model_data.get('type', '')
                model_info['nsfw'] = model_data.get('nsfw', False)
                model_info['poi'] = model_data.get('poi', False)
            
            json_data['model'] = model_info
            
            # 3. Model ID
            json_data['modelId'] = metadata.get('modelId')
            
            # 4. Model Version ID (renamed from 'id')
            json_data['modelVersionId'] = metadata.get('id')
            
            # 5. Trained Words
            json_data['trainedWords'] = metadata.get('trainedWords', [])
            
            # 6. Base Model
            json_data['baseModel'] = metadata.get('baseModel', '')
            
            # 7. Add timestamp
            json_data['last_updated'] = datetime.now().isoformat()
            
            # Save to file
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with json_path.open('w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved metadata: {json_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save metadata for {file_path.name}: {e}")
            return False

    def save_minimal_metadata(self, file_path: Path, sha256_hash: str) -> bool:
        """
        Save minimal metadata for files not found on Civitai
        
        Args:
            file_path: Path to the safetensor file
            sha256_hash: SHA256 hash of the file
            
        Returns:
            True if saved successfully, False otherwise
        """
        json_path = self.file_manager.get_json_path(file_path)
        
        try:
            json_data = OrderedDict()
            json_data['sha256'] = sha256_hash
            json_data['civitai_not_found'] = True
            json_data['last_updated'] = datetime.now().isoformat()
            
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with json_path.open('w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved minimal metadata: {json_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save minimal metadata for {file_path.name}: {e}")
            return False

    def download_images(self, file_hash_map: Dict[Path, str]) -> int:
        """
        Download preview images for models that have metadata
        
        Args:
            file_hash_map: Dictionary mapping file paths to their hashes (may be partial)
            
        Returns:
            Number of images successfully downloaded
        """
        from .progress_handler import ProgressBar
        
        downloaded_count = 0
        
        # Get ALL safetensor files in directory, not just those in file_hash_map
        all_safetensor_files = self.file_manager.find_safetensor_files()
        
        # Get all existing hashes (both computed and from existing JSON files)
        all_existing_hashes = self.file_manager.get_all_hashes()
        
        # Find files that have metadata and need images
        files_needing_images = []
        for file_path in all_safetensor_files:
            json_path = self.file_manager.get_json_path(file_path)
            json_data = self.file_manager.load_existing_json(json_path)
            
            # Skip if no metadata or not found on Civitai
            if not json_data or json_data.get('civitai_not_found'):
                continue
                
            preview_path = file_path.with_suffix('.preview.png')
            
            # Skip if image already exists and we're not forcing refresh
            if preview_path.exists() and not self.refresh_metadata:
                continue
                
            files_needing_images.append(file_path)
        
        if not files_needing_images:
            return 0
        
        # Create progress bar for image downloads
        progress = ProgressBar(len(files_needing_images), "Downloading preview images...")
        
        for i, file_path in enumerate(files_needing_images):
            try:
                # Get hash value - try from file_hash_map first, then from all_existing_hashes
                hash_value = None
                if file_path in file_hash_map:
                    hash_value = file_hash_map[file_path]
                elif str(file_path) in all_existing_hashes:
                    hash_value = all_existing_hashes[str(file_path)]
                else:
                    # If we still don't have a hash, try to get it from the JSON metadata
                    json_path = self.file_manager.get_json_path(file_path)
                    json_data = self.file_manager.load_existing_json(json_path)
                    if json_data and 'sha256' in json_data:
                        hash_value = json_data['sha256']
                
                if not hash_value:
                    logger.warning(f"No hash available for {file_path.name}, skipping image download")
                    progress.update(i + 1)
                    continue
                
                # Get metadata to find image URL
                metadata = self.api_client.get_model_by_hash(hash_value)
                
                if metadata:
                    image_url = self.api_client.get_primary_image_url(metadata)
                    if image_url:
                        preview_path = file_path.with_suffix('.preview.png')
                        if self.api_client.download_image(image_url, preview_path):
                            downloaded_count += 1
                
                progress.update(i + 1)
            except Exception as e:
                logger.error(f"Error downloading image for {file_path.name}: {e}")
                progress.update(i + 1)
        
        progress.finish(f"Image downloads completed - {downloaded_count} images downloaded")
        return downloaded_count

    # Add this method to the CivitaiProcessor class to replace the current process_directory results display

    def process_directory(self, download_images: bool = False) -> Dict[str, Any]:
        """
        Process entire directory: compute hashes, fetch metadata, save results
    
        Args:
            download_images: Whether to download preview images
        
        Returns:
            Dictionary containing processing results and statistics
        """        
        StatusDisplay.print_header(f"Starting sync for: {self.folder_path}")
    
        # Analyze directory for hash computation
        files_needing_hash, files_with_existing_hash = self.file_manager.analyze_directory()
    
        # Analyze metadata freshness
        files_needing_metadata, files_with_fresh_metadata = self.analyze_metadata_freshness()
    
        if not files_needing_hash and not files_with_existing_hash:
            StatusDisplay.print_warning("No safetensor files found in directory!")
            return {
                'success': False,
                'error': 'No safetensor files found',
                'stats': {'total_files': 0}
            }
    
        results = {
            'success': True,
            'stats': {
                'total_files': len(files_needing_hash) + len(files_with_existing_hash),
                'files_needing_hash': len(files_needing_hash),
            'files_with_existing_hash': len(files_with_existing_hash),
                'files_needing_metadata': len(files_needing_metadata),
                'files_with_fresh_metadata': len(files_with_fresh_metadata),
                'hashes_computed': 0,
                'metadata_fetched': 0,
                'files_saved': 0,
                'not_found': 0,
                'images_downloaded': 0,
                'errors': []
            }
        }
    
        try:
            # Show initial analysis
            StatusDisplay.print_info(f"Found {results['stats']['total_files']} safetensor files")
            if files_needing_metadata:
                StatusDisplay.print_info(f"{len(files_needing_metadata)} files need metadata update")
            
            # Compute missing hashes
            computed_hashes = {}
            if files_needing_hash:
                StatusDisplay.print_info(f"Computing hashes for {len(files_needing_hash)} files...")
                computed_hashes = self.compute_missing_hashes(files_needing_hash)
                results['stats']['hashes_computed'] = len(computed_hashes)
        
            # Get existing hashes
            existing_hashes = self.file_manager.get_all_hashes()
        
            # Combine all hashes for files that need metadata
            metadata_file_hashes = {}
        
            # Add computed hashes for files that need metadata
            for file_path in files_needing_metadata:
                if file_path in computed_hashes:
                    metadata_file_hashes[file_path] = computed_hashes[file_path]
                elif str(file_path) in existing_hashes:
                    metadata_file_hashes[file_path] = existing_hashes[str(file_path)]
                else:
                    logger.warning(f"No hash available for {file_path.name}")
        
            # Fetch and save metadata in one pass
            if metadata_file_hashes:
                StatusDisplay.print_info(f"Fetching metadata for {len(metadata_file_hashes)} files...")
                metadata_stats = self.fetch_and_save_metadata(metadata_file_hashes)
                results['stats']['metadata_fetched'] = metadata_stats['metadata_fetched']
                results['stats']['files_saved'] = metadata_stats['files_saved']
                results['stats']['not_found'] = metadata_stats['not_found']
                results['stats']['errors'].extend(metadata_stats['errors'])
        
            # Download images if requested
            if download_images:
                StatusDisplay.print_info("Downloading preview images...")
                # Combine all available hashes for image downloading
                all_file_hashes = {}
                all_file_hashes.update(computed_hashes)
                
                # Add existing hashes for files not in computed_hashes
                for file_path_str, hash_value in existing_hashes.items():
                    file_path = Path(file_path_str)
                    if file_path not in all_file_hashes:
                        all_file_hashes[file_path] = hash_value
                
                images_downloaded = self.download_images(all_file_hashes)
                results['stats']['images_downloaded'] = images_downloaded
        
            # Display final results with enhanced formatting
            StatusDisplay.print_results(results['stats'])
        
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            StatusDisplay.print_error(f"Processing failed: {e}")
            results['success'] = False
            results['error'] = str(e)
            results['stats']['errors'].append(str(e))
    
        finally:
            # Clean up API client
            self.api_client.close()
    
        return results


def process_civitai_directory(folder_path: str, api_key: Optional[str] = None, 
                             rate_limit_delay: float = 1.0, refresh_metadata: bool = False,
                             max_metadata_age_days: int = 30, download_images: bool = False) -> Dict[str, Any]:
    """
    Convenience function to process a directory with Civitai integration
    
    Args:
        folder_path: Path to folder containing safetensor files
        api_key: Optional Civitai API key
        rate_limit_delay: Delay between API requests in seconds
        refresh_metadata: Force refresh of all metadata
        max_metadata_age_days: Maximum age of metadata before refresh
        download_images: Whether to download preview images
        
    Returns:
        Dictionary containing processing results
    """
    processor = CivitaiProcessor(
        folder_path, api_key, rate_limit_delay, 
        refresh_metadata, max_metadata_age_days
    )
    return processor.process_directory(download_images)