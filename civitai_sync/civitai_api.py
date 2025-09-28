"""
Enhanced Civitai API client with retry logic and image downloading
"""

import requests
import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import random

logger = logging.getLogger(__name__)


class CivitaiAPIClient:
    """Enhanced client for interacting with Civitai API"""
    
    def __init__(self, api_key: Optional[str] = None, rate_limit_delay: float = 1.0):
        """Initialize Civitai API client"""
        self.api_key = api_key
        self.base_url = "https://civitai.com/api/v1"
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'civitai-sync/1.0'
        })
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _exponential_backoff(self, attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        """Calculate exponential backoff delay with jitter"""
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = delay * 0.1 * random.random()
        return delay + jitter
    
    def _make_request_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and exponential backoff"""
        for attempt in range(max_retries + 1):
            self._wait_for_rate_limit()
            
            try:
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 429:  # Too Many Requests
                    if attempt < max_retries:
                        backoff_delay = self._exponential_backoff(attempt)
                        logger.warning(f"Rate limited, backing off for {backoff_delay:.2f}s (attempt {attempt + 1})")
                        time.sleep(backoff_delay)
                        continue
                    else:
                        logger.error(f"Rate limited after {max_retries} retries")
                        return None
                
                if response.status_code == 404:
                    logger.debug(f"Resource not found: {url}")
                    return response
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    backoff_delay = self._exponential_backoff(attempt)
                    logger.warning(f"Request timeout, retrying in {backoff_delay:.2f}s (attempt {attempt + 1})")
                    time.sleep(backoff_delay)
                    continue
                else:
                    logger.error(f"Request timeout after {max_retries} retries")
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    backoff_delay = self._exponential_backoff(attempt)
                    logger.warning(f"Request failed: {e}, retrying in {backoff_delay:.2f}s (attempt {attempt + 1})")
                    time.sleep(backoff_delay)
                    continue
                else:
                    logger.error(f"Request failed after {max_retries} retries: {e}")
                    return None
        
        return None
    
    def get_model_by_hash(self, sha256_hash: str) -> Optional[Dict[Any, Any]]:
        """Fetch model metadata from Civitai by SHA256 hash"""
        url = f"{self.base_url}/model-versions/by-hash/{sha256_hash}"
        
        logger.info(f"Fetching metadata for hash: {sha256_hash[:8]}...")
        response = self._make_request_with_retry(url)
        
        if not response:
            return None
        
        if response.status_code == 404:
            logger.warning(f"Model not found for hash: {sha256_hash[:8]}...")
            return None
        
        try:
            data = response.json()
            data['computed_hash'] = sha256_hash
            logger.info(f"Successfully fetched metadata for hash: {sha256_hash[:8]}...")
            return data
        except ValueError as e:
            logger.error(f"Invalid JSON response for hash {sha256_hash[:8]}...: {e}")
            return None
    
    def download_image(self, image_url: str, output_path: Path) -> bool:
        """Download an image from URL to local file"""
        logger.info(f"Downloading image: {output_path.name}")

        if not self._is_valid_image_url(image_url):
            logger.warning(f"URL does not point to a valid image: {image_url}")
            return False
        
        response = self._make_request_with_retry(image_url)
        if not response:
            logger.error(f"Failed to download image: {image_url}")
            return False
        
        try:
            content_type = response.headers.get('content-type', '').lower()
            extension_map = {
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/png': '.png',
                'image/webp': '.webp',
                'image/gif': '.gif',
                'image/bmp': '.bmp',
                'image/tiff': '.tiff'
            }
            proper_extension = extension_map.get(content_type, '.png')
        
            if not output_path.name.endswith(proper_extension):
                base_name = output_path.name.replace('.preview.png', '')
                output_path = output_path.parent / f"{base_name}.preview{proper_extension}"
        
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with output_path.open('wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"✓ Downloaded image: {output_path.name}")
            return True
            
        except IOError as e:
            logger.error(f"Failed to save image {output_path}: {e}")
            return False
    
    def get_image_urls_from_metadata(self, metadata: Dict[Any, Any]) -> list[str]:
        """Extract all image URLs from model metadata"""
        image_urls = []
        
        if 'images' in metadata and isinstance(metadata['images'], list):
            for image_data in metadata['images']:
                if isinstance(image_data, dict) and 'url' in image_data:
                    image_urls.append(image_data['url'])
        
        if 'model' in metadata and isinstance(metadata['model'], dict):
            model_data = metadata['model']
            if 'images' in model_data and isinstance(model_data['images'], list):
                for image_data in model_data['images']:
                    if isinstance(image_data, dict) and 'url' in image_data:
                        image_urls.append(image_data['url'])
        
        return image_urls
    
    def get_primary_image_url(self, metadata: Dict[Any, Any]) -> Optional[str]:
        """Get the first valid image URL from metadata, skipping videos"""
        image_urls = self.get_image_urls_from_metadata(metadata)
    
        if not image_urls:
            return None
    
        for url in image_urls:
            if self._is_valid_image_url(url):
                logger.debug(f"Found valid image URL: {url}")
                return url
            else:
                logger.debug(f"Skipping non-image URL: {url}")
    
        logger.warning("No valid image URLs found in metadata")
        return None

    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL points to a valid image by examining the response"""
        try:
            # First check the URL extension
            url_lower = url.lower()
            video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.gif']
            if any(url_lower.endswith(ext) for ext in video_extensions):
                return False
            
            # Make a HEAD request to check content type
            response = self.session.head(url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                return content_type.startswith('image/')
            
            # If HEAD fails, try a small GET request
            response = self.session.get(url, timeout=10, stream=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                return content_type.startswith('image/')
            
            return False
            
        except Exception as e:
            logger.debug(f"Error validating image URL {url}: {e}")
            return False
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()