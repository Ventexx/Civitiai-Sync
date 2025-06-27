"""
Enhanced utilities for computing SHA256 hashes of safetensor files
"""

import hashlib
import logging
from pathlib import Path
from typing import Union
import json

logger = logging.getLogger(__name__)


def compute_sha256(file_path: Union[str, Path], chunk_size: int = 8192, quiet: bool = False) -> str:
    """
    Compute SHA256 hash of a file with progress logging for large files
    
    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time (default 8KB)
        quiet: If True, suppress progress logging
        
    Returns:
        SHA256 hash as lowercase hexadecimal string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    file_size = file_path.stat().st_size
    if not quiet:
        logger.debug(f"Computing SHA256 for: {file_path.name} ({file_size / (1024*1024):.1f} MB)")
    
    sha256_hash = hashlib.sha256()
    bytes_processed = 0
    
    try:
        with file_path.open('rb') as f:
            # Read file in chunks to handle large files efficiently
            while chunk := f.read(chunk_size):
                sha256_hash.update(chunk)
                bytes_processed += len(chunk)
                
                # Log progress for large files (>100MB) only if not quiet
                if not quiet and file_size > 100 * 1024 * 1024:
                    progress = (bytes_processed / file_size) * 100
                    if bytes_processed % (10 * 1024 * 1024) == 0:  # Every 10MB
                        logger.debug(f"Progress: {progress:.1f}% ({bytes_processed / (1024*1024):.1f} MB)")
        
        result = sha256_hash.hexdigest().lower()
        if not quiet:
            logger.debug(f"SHA256 computed for {file_path.name}: {result[:8]}...")
        return result
        
    except IOError as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def verify_safetensor_file(file_path: Union[str, Path]) -> bool:
    """
    Verify that a file is a valid safetensor file with enhanced checks
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file appears to be a valid safetensor file
    """
    file_path = Path(file_path)
    
    # Check file extension
    if file_path.suffix.lower() not in ['.safetensors', '.safetensor']:
        logger.debug(f"Invalid extension for {file_path.name}")
        return False
    
    # Check if file exists and is not empty
    if not file_path.exists():
        logger.debug(f"File does not exist: {file_path.name}")
        return False
    
    file_size = file_path.stat().st_size
    if file_size == 0:
        logger.debug(f"File is empty: {file_path.name}")
        return False
    
    # Minimum reasonable size for a safetensor file (header + some data)
    if file_size < 100:
        logger.debug(f"File too small to be valid safetensor: {file_path.name}")
        return False
    
    # Basic header check - safetensor files start with a JSON header
    try:
        with file_path.open('rb') as f:
            # Read first 8 bytes to check for JSON header length
            header_length_bytes = f.read(8)
            if len(header_length_bytes) < 8:
                logger.debug(f"Header too short: {file_path.name}")
                return False
            
            # Safetensor files start with an 8-byte little-endian integer
            # indicating the JSON header length
            header_length = int.from_bytes(header_length_bytes, byteorder='little')
            
            # Reasonable bounds check for header length
            if header_length < 10 or header_length > (file_size - 8):
                logger.debug(f"Invalid header length {header_length}: {file_path.name}")
                return False
            
            # Check if file is long enough to contain the header
            if file_size < 8 + header_length:
                logger.debug(f"File too short for declared header length: {file_path.name}")
                return False
            
            # Try to read the JSON header
            header_data = f.read(header_length)
            if len(header_data) != header_length:
                logger.debug(f"Could not read full header: {file_path.name}")
                return False
            
            # Try to decode as JSON (basic validation)
            try:
                header_json = json.loads(header_data.decode('utf-8'))
                
                # Basic structure validation - should be a dict
                if not isinstance(header_json, dict):
                    logger.debug(f"Header is not a JSON object: {file_path.name}")
                    return False
                
                # Check for expected keys in safetensor header
                if '__metadata__' not in header_json:
                    logger.debug(f"Missing __metadata__ in header: {file_path.name}")
                    # This is not strictly required, so we'll allow it
                
                logger.debug(f"Valid safetensor file: {file_path.name}")
                return True
                
            except json.JSONDecodeError as e:
                logger.debug(f"Invalid JSON in header: {file_path.name} - {e}")
                return False
            except UnicodeDecodeError as e:
                logger.debug(f"Invalid UTF-8 in header: {file_path.name} - {e}")
                return False
            
    except (IOError, MemoryError) as e:
        logger.debug(f"Error reading file {file_path.name}: {e}")
        return False


def get_safetensor_metadata(file_path: Union[str, Path]) -> dict:
    """
    Extract metadata from a safetensor file header
    
    Args:
        file_path: Path to the safetensor file
        
    Returns:
        Dictionary containing metadata, empty dict if none found
    """
    file_path = Path(file_path)
    
    if not verify_safetensor_file(file_path):
        return {}
    
    try:
        with file_path.open('rb') as f:
            # Read header length
            header_length_bytes = f.read(8)
            header_length = int.from_bytes(header_length_bytes, byteorder='little')
            
            # Read header
            header_data = f.read(header_length)
            header_json = json.loads(header_data.decode('utf-8'))
            
            # Extract metadata
            metadata = header_json.get('__metadata__', {})
            
            # Add some computed info
            metadata['_file_size'] = file_path.stat().st_size
            metadata['_header_size'] = header_length
            metadata['_tensor_count'] = len([k for k in header_json.keys() if k != '__metadata__'])
            
            return metadata
            
    except Exception as e:
        logger.error(f"Error extracting metadata from {file_path.name}: {e}")
        return {}


def validate_sha256_hash(hash_string: str) -> bool:
    """
    Validate that a string is a valid SHA256 hash
    
    Args:
        hash_string: String to validate
        
    Returns:
        True if valid SHA256 hash format
    """
    if not isinstance(hash_string, str):
        return False
    
    # Remove any whitespace
    hash_string = hash_string.strip().lower()
    
    # SHA256 should be exactly 64 hex characters
    if len(hash_string) != 64:
        return False
    
    # Check if all characters are valid hex
    return all(c in '0123456789abcdef' for c in hash_string)