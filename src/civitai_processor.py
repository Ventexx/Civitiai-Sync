"""
Enhanced processor for handling Civitai API integration with local safetensor files
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .civitai_api import CivitaiAPIClient
from .file_manager import FileManager
from .hash_utils import compute_sha256, verify_safetensor_file

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
        
        return valid_files
    
    def compute_missing_hashes(self, files_needing_hash: List[Path]) -> Dict[Path, str]:
        """
        Compute SHA256 hashes for files that don't have them
        
        Args:
            files_needing_hash: List of files that need hash computation
            
        Returns:
            Dictionary mapping file paths to their computed hashes
        """
        computed_hashes = {}
        
        # Validate files first
        valid_files = self.validate_safetensor_files(files_needing_hash)
        
        if len(valid_files) != len(files_needing_hash):
            logger.warning(f"Skipping {len(files_needing_hash) - len(valid_files)} invalid files")
        
        for file_path in valid_files:
            try:
                hash_value = compute_sha256(file_path)
                computed_hashes[file_path] = hash_value
            except Exception as e:
                logger.error(f"Failed to compute hash for {file_path.name}: {e}")
        
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
        metadata_results = {}
        
        total_files = len(file_hash_map)
        logger.info(f"Fetching Civitai metadata for {total_files} files...")
        
        for i, (file_path, hash_value) in enumerate(file_hash_map.items(), 1):
            logger.info(f"Processing {i}/{total_files}: {file_path.name}")
            
            try:
                metadata = self.api_client.get_model_by_hash(hash_value)
                metadata_results[file_path] = metadata
                
                if metadata:
                    logger.info(f"✓ Found metadata for {file_path.name}")
                else:
                    logger.info(f"✗ No metadata found for {file_path.name}")
                    
            except Exception as e:
                logger.error(f"Error fetching metadata for {file_path.name}: {e}")
                metadata_results[file_path] = None
        
        return metadata_results
    
    def download_images(self, file_metadata_map: Dict[Path, Optional[Dict[Any, Any]]]) -> int:
        """
        Download preview images for models with metadata
        
        Args:
            file_metadata_map: Dictionary mapping file paths to their metadata
            
        Returns:
            Number of images successfully downloaded
        """
        downloaded_count = 0
        
        logger.info("Starting image download process...")
        
        for file_path, metadata in file_metadata_map.items():
            if not metadata:
                continue
            
            # Get primary image URL
            image_url = self.api_client.get_primary_image_url(metadata)
            if not image_url:
                logger.debug(f"No image found for {file_path.name}")
                continue
            
            # Create preview image path
            preview_path = file_path.with_suffix('.preview.png')
            
            # Skip if image already exists and we're not forcing refresh
            if preview_path.exists() and not self.refresh_metadata:
                logger.debug(f"Preview image already exists: {preview_path.name}")
                continue
            
            # Download image
            try:
                if self.api_client.download_image(image_url, preview_path):
                    downloaded_count += 1
                else:
                    logger.warning(f"Failed to download image for {file_path.name}")
            except Exception as e:
                logger.error(f"Error downloading image for {file_path.name}: {e}")
        
        logger.info(f"Downloaded {downloaded_count} preview images")
        return downloaded_count
    
    def save_metadata_to_json(self, file_metadata_map: Dict[Path, Optional[Dict[Any, Any]]], 
                             file_hash_map: Dict[Path, str]) -> int:
        """
        Save metadata to corresponding JSON files
        
        Args:
            file_metadata_map: Dictionary mapping file paths to their metadata
            file_hash_map: Dictionary mapping file paths to their hashes
            
        Returns:
            Number of files successfully saved
        """
        saved_count = 0
        current_time = datetime.now().isoformat()
        
        for file_path, metadata in file_metadata_map.items():
            json_path = self.file_manager.get_json_path(file_path)
            hash_value = file_hash_map.get(file_path)
            
            # Load existing JSON if it exists
            existing_data = self.file_manager.load_existing_json(json_path) or {}
            
            # Create the data to save
            json_data = {
                'computed_hash': hash_value,
                'last_updated': current_time,
                **existing_data  # Preserve any existing data
            }
            
            # Add Civitai metadata if available
            if metadata:
                json_data['civitai_metadata'] = metadata
                # Remove the not_found flag if it exists
                json_data.pop('civitai_not_found', None)
            else:
                json_data['civitai_metadata'] = None
                json_data['civitai_not_found'] = True
            
            # Save to JSON file
            if self.file_manager.save_json(json_path, json_data):
                saved_count += 1
            else:
                logger.error(f"Failed to save JSON for {file_path.name}")
        
        return saved_count
    
    def process_directory(self, download_images: bool = False) -> Dict[str, Any]:
        """
        Process entire directory: compute hashes, fetch metadata, save results
        
        Args:
            download_images: Whether to download preview images
            
        Returns:
            Dictionary containing processing results and statistics
        """
        logger.info(f"Starting processing of directory: {self.folder_path}")
        
        # Analyze directory for hash computation
        files_needing_hash, files_with_existing_hash = self.file_manager.analyze_directory()
        
        # Analyze metadata freshness
        files_needing_metadata, files_with_fresh_metadata = self.analyze_metadata_freshness()
        
        if not files_needing_hash and not files_with_existing_hash:
            logger.warning("No safetensor files found in directory!")
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
                logger.info(f"Computing hashes for {len(files_needing_hash)} files...")
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
            
            # Fetch metadata from Civitai only for files that need it
            metadata_results = {}
            if metadata_file_hashes:
                logger.info(f"Fetching Civitai metadata for {len(metadata_file_hashes)} files...")
                metadata_results = self.fetch_civitai_metadata(metadata_file_hashes)
                
                # Count successful metadata fetches
                metadata_found = sum(1 for metadata in metadata_results.values() if metadata is not None)
                results['stats']['metadata_fetched'] = metadata_found
                
                # Save results to JSON files
                logger.info("Saving results to JSON files...")
                saved_count = self.save_metadata_to_json(metadata_results, metadata_file_hashes)
                results['stats']['files_saved'] = saved_count
            
            # Download images if requested
            if download_images and metadata_results:
                logger.info("Starting image download process...")
                images_downloaded = self.download_images(metadata_results)
                results['stats']['images_downloaded'] = images_downloaded
            
            logger.info(f"Processing complete! Stats: {results['stats']}")
            
        except Exception as e:
            logger.error(f"Error during processing: {e}")
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