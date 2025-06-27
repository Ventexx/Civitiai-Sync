"""
Enhanced processor for handling Civitai API integration with local safetensor files
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import OrderedDict

from .civitai_api import CivitaiAPIClient
from .file_manager import FileManager
from .hash_utils import compute_sha256, verify_safetensor_file
from .metadata_saver import MetadataSaver

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
        
        # Check if we have civitai metadata
        if 'civitai_metadata' not in json_data or json_data['civitai_metadata'] is None:
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
    
    def fetch_civitai_metadata(self, file_hash_map: Dict[Path, str]) -> Dict[Path, Optional[Dict[Any, Any]]]:
        """
        Fetch metadata from Civitai for all hashes
        
        Args:
            file_hash_map: Dictionary mapping file paths to their hashes
            
        Returns:
            Dictionary mapping file paths to their Civitai metadata (or None if not found)
        """
        from .progress_handler import ProgressBar
        
        metadata_results = {}
        
        if not file_hash_map:
            return metadata_results
        
        # Create progress bar for API calls
        progress = ProgressBar(len(file_hash_map), "Fetching metadata from Civitai API...")
        
        for i, (file_path, hash_value) in enumerate(file_hash_map.items(), 1):
            try:
                metadata = self.api_client.get_model_by_hash(hash_value)
                metadata_results[file_path] = metadata
                progress.update(i)
                    
            except Exception as e:
                logger.error(f"Error fetching metadata for {file_path.name}: {e}")
                metadata_results[file_path] = None
                progress.update(i)
        
        # Count successful fetches for final message
        metadata_found = sum(1 for metadata in metadata_results.values() if metadata is not None)
        progress.finish(f"API calls completed - {metadata_found} models found")
        
        return metadata_results

    def fetch_additional_metadata(self, version_id: int, model_id: int) -> Dict[str, Any]:
        """
        Call out to MetadataSaver.fetch_additional_metadata (stub) so that
        when the real endpoint exists, you’ll just need to implement it there.
        """
        return MetadataSaver(Path()).fetch_additional_metadata(
            self.api_client, version_id, model_id
        )

    def download_images(self, file_metadata_map: Dict[Path, Optional[Dict[Any, Any]]]) -> int:
        """
        Download preview images for models with metadata
        
        Args:
            file_metadata_map: Dictionary mapping file paths to their metadata
            
        Returns:
            Number of images successfully downloaded
        """
        from .progress_handler import ProgressBar
        
        downloaded_count = 0
        
        # Count files that have images to download
        files_with_images = []
        for file_path, metadata in file_metadata_map.items():
            if not metadata:
                continue
            
            image_url = self.api_client.get_primary_image_url(metadata)
            if not image_url:
                continue
                
            preview_path = file_path.with_suffix('.preview.png')
            
            # Skip if image already exists and we're not forcing refresh
            if preview_path.exists() and not self.refresh_metadata:
                continue
                
            files_with_images.append((file_path, image_url, preview_path))
        
        if not files_with_images:
            return 0
        
        # Create progress bar for image downloads
        progress = ProgressBar(len(files_with_images), "Downloading preview images...")
        
        for i, (file_path, image_url, preview_path) in enumerate(files_with_images):
            try:
                if self.api_client.download_image(image_url, preview_path):
                    downloaded_count += 1
                progress.update(i + 1)
            except Exception as e:
                logger.error(f"Error downloading image for {file_path.name}: {e}")
                progress.update(i + 1)
        
        progress.finish(f"Image downloads completed - {downloaded_count} images downloaded")
        return downloaded_count

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
                'images_downloaded': 0,
                'errors': []
            }
        }
        
        try:
            # Compute missing hashes
            computed_hashes = {}
            if files_needing_hash:
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
            
            metadata_results = {}
            if metadata_file_hashes:
                # 1) Fetch initial metadata by hash
                metadata_results = self.fetch_civitai_metadata(metadata_file_hashes)

                for file_path, initial_meta in metadata_results.items():
                    sha256 = metadata_file_hashes[file_path]
                    json_path = self.file_manager.get_json_path(file_path)

                    # 2) Instantiate saver and write initial + placeholder additional
                    saver = MetadataSaver(json_path)
                    # initial_meta may be None if not found
                    # Attempt to fetch the "additional" data by version/model IDs
                    additional_meta = None
                    if initial_meta:
                        version_id = initial_meta.get('id')
                        model_id   = initial_meta.get('modelId')
                        additional_meta = saver.fetch_additional_metadata(version_id, model_id)

                    if saver.write_metadata(sha256, initial_meta or {}, additional_meta):
                        results['stats']['files_saved'] += 1
                    else:
                        logger.error(f"Failed to save JSON for {file_path.name}")
            
            # Download images if requested
            if download_images and metadata_results:
                images_downloaded = self.download_images(metadata_results)
                results['stats']['images_downloaded'] = images_downloaded
            
            # Display final results
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
