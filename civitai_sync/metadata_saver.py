import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from collections import OrderedDict
from datetime import datetime

logger = logging.getLogger(__name__)


class MetadataSaver:
    """Simplified metadata saver - functionality moved to CivitaiProcessor."""
    
    def __init__(self, json_path: Path):
        self.json_path = json_path
    
    def load_json_file(self) -> Optional[Dict[str, Any]]:
        """Load JSON file if it exists."""
        if not self.json_path.exists():
            return None
        
        try:
            with self.json_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading JSON file {self.json_path.name}: {e}")
            return None
    
    def save_json_file(self, data: Dict[str, Any]) -> bool:
        """Save data to JSON file."""
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            with self.json_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error(f"Error saving JSON file {self.json_path.name}: {e}")
            return False
    
    def fetch_additional_metadata(self, version_id: Optional[int], model_id: Optional[int]) -> Dict[str, Any]:
        """Placeholder for additional metadata fetching."""
        return {}
    
    def write_metadata(self, sha256_hash: str, initial_meta: Dict[str, Any], 
                      additional_meta: Optional[Dict[str, Any]] = None) -> bool:
        """Write metadata in the specified format."""
        try:
            if not initial_meta:
                # Save minimal metadata for files not found on Civitai
                json_data = OrderedDict()
                json_data['sha256'] = sha256_hash
                json_data['civitai_not_found'] = True
                json_data['last_updated'] = datetime.now().isoformat()
            else:
                # Create ordered dictionary with specified structure and order
                json_data = OrderedDict()
                
                # SHA256 hash (always first)
                json_data['sha256'] = sha256_hash
                
                # Model info (extracted from metadata)
                model_info = OrderedDict()
                if 'model' in initial_meta:
                    model_data = initial_meta['model']
                    model_info['name'] = model_data.get('name', '')
                    model_info['type'] = model_data.get('type', '')
                    model_info['nsfw'] = model_data.get('nsfw', False)
                    model_info['poi'] = model_data.get('poi', False)
                json_data['model'] = model_info
                
                json_data['modelId'] = initial_meta.get('modelId')
                json_data['modelVersionId'] = initial_meta.get('id')
                json_data['trainedWords'] = initial_meta.get('trainedWords', [])
                json_data['baseModel'] = initial_meta.get('baseModel', '')
                json_data['last_updated'] = datetime.now().isoformat()
            
            return self.save_json_file(json_data)
            
        except Exception as e:
            logger.error(f"Failed to write metadata: {e}")
            return False


def process_civitai_models(directory_path: Union[str, Path], 
                          api_key: Optional[str] = None,
                          rate_limit_delay: float = 1.0) -> Dict[str, Any]:
    """Process all safetensor files in a directory for Civitai model information."""
    from .civitai_processor import process_civitai_directory
    
    return process_civitai_directory(
        folder_path=str(directory_path),
        api_key=api_key,
        rate_limit_delay=rate_limit_delay
    )