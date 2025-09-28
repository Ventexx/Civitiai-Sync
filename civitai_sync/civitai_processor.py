"""
Enhanced processor for handling Civitai API integration with local safetensor files
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
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
                 rate_limit_delay: float = 1.0):
        """Initialize CivitaiProcessor with folder path and API settings"""
        self.file_manager = FileManager(folder_path)
        self.api_client = CivitaiAPIClient(api_key, rate_limit_delay)
        self.folder_path = Path(folder_path)
    
    def validate_safetensor_files(self, files: List[Path]) -> List[Path]:
        """Validate that files are proper safetensor files, return only valid ones"""
        valid_files = []
        
        for file_path in files:
            if verify_safetensor_file(file_path):
                valid_files.append(file_path)
            else:
                logger.warning(f"Invalid or corrupted safetensor file: {file_path.name}")
        
        if files and not valid_files:
            logger.error("All safetensor files are invalid or corrupted; aborting.")
            raise ValueError("No valid safetensor files found")

        return valid_files
    
    def compute_missing_hashes(self, files_needing_hash: List[Path]) -> Dict[Path, str]:
        """Compute SHA256 hashes for files that don't have them"""
        from .progress_handler import ProgressBar
        
        computed_hashes = {}
        valid_files = self.validate_safetensor_files(files_needing_hash)
        
        if len(valid_files) != len(files_needing_hash):
            logger.warning(f"Skipping {len(files_needing_hash) - len(valid_files)} invalid files")
        
        if not valid_files:
            return computed_hashes
        
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
    
    def _has_complete_metadata(self, json_data: Dict[Any, Any]) -> bool:
        """Check if JSON contains complete metadata or not-found flag"""
        if json_data.get('civitai_not_found'):
            return True
        
        required_fields = ['model', 'modelId', 'modelVersionId']
        return all(field in json_data for field in required_fields)
    
    def fetch_and_save_metadata(self, file_hash_map: Dict[Path, str]) -> Dict[str, Any]:
        """Fetch metadata from Civitai and save it in JSON format"""
        from .progress_handler import ProgressBar
        
        stats = {
            'metadata_fetched': 0,
            'files_saved': 0,
            'not_found': 0,
            'errors': []
        }
        
        if not file_hash_map:
            return stats
        
        progress = ProgressBar(len(file_hash_map), "Fetching and saving metadata...")
        
        for i, (file_path, hash_value) in enumerate(file_hash_map.items(), 1):
            try:
                metadata = self.api_client.get_model_by_hash(hash_value)
                
                if metadata:
                    stats['metadata_fetched'] += 1
                    
                    if self.save_metadata_file(file_path, hash_value, metadata):
                        stats['files_saved'] += 1
                    else:
                        stats['errors'].append(f"Failed to save metadata for {file_path.name}")
                else:
                    stats['not_found'] += 1
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
        """Save metadata to JSON file in ordered format"""
        json_path = self.file_manager.get_json_path(file_path)
        
        try:
            json_data = OrderedDict()
            
            json_data['sha256'] = sha256_hash
            
            model_info = OrderedDict()
            
            model_data = None
            if 'model' in metadata and isinstance(metadata['model'], dict):
                model_data = metadata['model']
            elif isinstance(metadata, dict):
                model_data = metadata
            
            if model_data:
                model_info['name'] = model_data.get('name', '')
                model_info['type'] = model_data.get('type', '')
                model_info['nsfw'] = model_data.get('nsfw', False)
                model_info['poi'] = model_data.get('poi', False)
            
            json_data['model'] = model_info
            json_data['modelId'] = metadata.get('modelId')
            json_data['modelVersionId'] = metadata.get('id')
            json_data['trainedWords'] = metadata.get('trainedWords', [])
            json_data['baseModel'] = metadata.get('baseModel', '')
            json_data['last_updated'] = datetime.now().isoformat()
            
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with json_path.open('w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved metadata: {json_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save metadata for {file_path.name}: {e}")
            return False

    def save_minimal_metadata(self, file_path: Path, sha256_hash: str) -> bool:
        """Save minimal metadata for files not found on Civitai"""
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
        """Download preview images for models that have metadata"""
        from .progress_handler import ProgressBar
        
        downloaded_count = 0
        
        all_safetensor_files = self.file_manager.find_safetensor_files()
        all_existing_hashes = self.file_manager.get_all_hashes()
        
        files_needing_images = []
        for file_path in all_safetensor_files:
            json_path = self.file_manager.get_json_path(file_path)
            json_data = self.file_manager.load_existing_json(json_path)
            
            if not json_data or json_data.get('civitai_not_found'):
                continue
            
            # Check for any preview image with common extensions
            preview_extensions = ['.preview.png', '.preview.jpg', '.preview.jpeg', '.preview.webp', '.preview.gif']
            has_preview = any((file_path.parent / (file_path.stem + ext)).exists() for ext in preview_extensions)
            
            if has_preview:
                continue
                
            files_needing_images.append(file_path)
        
        if not files_needing_images:
            return 0
        
        progress = ProgressBar(len(files_needing_images), "Downloading preview images...")
        
        for i, file_path in enumerate(files_needing_images):
            try:
                hash_value = None
                if file_path in file_hash_map:
                    hash_value = file_hash_map[file_path]
                elif str(file_path) in all_existing_hashes:
                    hash_value = all_existing_hashes[str(file_path)]
                else:
                    json_path = self.file_manager.get_json_path(file_path)
                    json_data = self.file_manager.load_existing_json(json_path)
                    if json_data and 'sha256' in json_data:
                        hash_value = json_data['sha256']
                
                if not hash_value:
                    logger.warning(f"No hash available for {file_path.name}, skipping image download")
                    progress.update(i + 1)
                    continue
                
                metadata = self.api_client.get_model_by_hash(hash_value)
                
                if metadata:
                    image_url = self.api_client.get_primary_image_url(metadata)
                    if image_url:
                        # Start with .png, but download_image will adjust extension based on actual content
                        preview_path = file_path.with_suffix('.preview.png')
                        if self.api_client.download_image(image_url, preview_path):
                            downloaded_count += 1
                    else:
                        logger.info(f"No valid images available for {file_path.name}")
                
                progress.update(i + 1)
            except Exception as e:
                logger.error(f"Error downloading image for {file_path.name}: {e}")
                progress.update(i + 1)
        
        progress.finish(f"Image downloads completed - {downloaded_count} images downloaded")
        return downloaded_count
        
    def process_directory(self, download_images: bool = False) -> Dict[str, Any]:
        """Process entire directory: compute hashes, fetch metadata, save results"""      
        StatusDisplay.print_header(f"Starting sync for: {self.folder_path}")

        files_needing_hash, files_with_existing_hash = self.file_manager.analyze_directory()

        if not files_needing_hash and not files_with_existing_hash:
            StatusDisplay.print_warning("No safetensor files found in directory!")
            return {
                'success': False,
                'error': 'No safetensor files found',
                'stats': {'total_files': 0}
            }

        all_safetensor_files = self.file_manager.find_safetensor_files()
        files_needing_metadata = []
        
        for safetensor_file in all_safetensor_files:
            json_path = self.file_manager.get_json_path(safetensor_file)
            existing_json = self.file_manager.load_existing_json(json_path)
            
            if not existing_json or not self._has_complete_metadata(existing_json):
                files_needing_metadata.append(safetensor_file)

        results = {
            'success': True,
            'stats': {
                'total_files': len(all_safetensor_files),
                'files_needing_hash': len(files_needing_hash),
                'files_with_existing_hash': len(files_with_existing_hash),
                'files_needing_metadata': len(files_needing_metadata),
                'hashes_computed': 0,
                'metadata_fetched': 0,
                'files_saved': 0,
                'not_found': 0,
                'images_downloaded': 0,
                'errors': []
            }
        }

        try:
            StatusDisplay.print_info(f"Found {results['stats']['total_files']} safetensor files")
            if files_needing_metadata:
                StatusDisplay.print_info(f"{len(files_needing_metadata)} files need metadata")
            
            computed_hashes = {}
            if files_needing_hash:
                StatusDisplay.print_info(f"Computing hashes for {len(files_needing_hash)} files...")
                computed_hashes = self.compute_missing_hashes(files_needing_hash)
                results['stats']['hashes_computed'] = len(computed_hashes)
        
            existing_hashes = self.file_manager.get_all_hashes()
        
            metadata_file_hashes = {}
        
            for file_path in files_needing_metadata:
                if file_path in computed_hashes:
                    metadata_file_hashes[file_path] = computed_hashes[file_path]
                elif str(file_path) in existing_hashes:
                    metadata_file_hashes[file_path] = existing_hashes[str(file_path)]
                else:
                    logger.warning(f"No hash available for {file_path.name}")
        
            if metadata_file_hashes:
                StatusDisplay.print_info(f"Fetching metadata for {len(metadata_file_hashes)} files...")
                metadata_stats = self.fetch_and_save_metadata(metadata_file_hashes)
                results['stats']['metadata_fetched'] = metadata_stats['metadata_fetched']
                results['stats']['files_saved'] = metadata_stats['files_saved']
                results['stats']['not_found'] = metadata_stats['not_found']
                results['stats']['errors'].extend(metadata_stats['errors'])
        
            if download_images:
                StatusDisplay.print_info("Downloading preview images...")
                all_file_hashes = {}
                all_file_hashes.update(computed_hashes)
                
                for file_path_str, hash_value in existing_hashes.items():
                    file_path = Path(file_path_str)
                    if file_path not in all_file_hashes:
                        all_file_hashes[file_path] = hash_value
                
                images_downloaded = self.download_images(all_file_hashes)
                results['stats']['images_downloaded'] = images_downloaded
        
            StatusDisplay.print_results(results['stats'])
        
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            StatusDisplay.print_error(f"Processing failed: {e}")
            results['success'] = False
            results['error'] = str(e)
            results['stats']['errors'].append(str(e))

        finally:
            self.api_client.close()

        return results


def process_civitai_directory(folder_path: str, api_key: Optional[str] = None, 
                             rate_limit_delay: float = 1.0, download_images: bool = False) -> Dict[str, Any]:
    """Convenience function to process a directory with Civitai integration"""
    processor = CivitaiProcessor(folder_path, api_key, rate_limit_delay)
    return processor.process_directory(download_images)