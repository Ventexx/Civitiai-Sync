#!/usr/bin/env python3

import sys
from pathlib import Path
import argparse
import logging

from civitai_sync.civitai_processor import CivitaiProcessor
from civitai_sync.config_manager import ConfigManager
from civitai_sync.progress_handler import StatusDisplay


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def save_api_key(api_key: str) -> bool:
    """Save API key to config."""
    config_manager = ConfigManager()
    return config_manager.save_api_key(api_key)


def main():
    parser = argparse.ArgumentParser(
        description='Sync safetensor model metadata and images from Civitai',
        prog='civitai-sync'
    )
    
    parser.add_argument(
        'folder_path',
        nargs='?',
        help='Path to folder containing safetensor files'
    )
    
    parser.add_argument(
        '--api-key',
        help='Civitai API key for this session'
    )
    
    parser.add_argument(
        '--save-api-key',
        metavar='API_KEY',
        help='Save API key to local config for future use'
    )
    
    parser.add_argument(
        '--img', '--images',
        action='store_true',
        help='Download preview images for models'
    )
    
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Delay between API requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress all output except errors'
    )
    
    args = parser.parse_args()
    
    # Handle API key saving
    if args.save_api_key:
        if save_api_key(args.save_api_key):
            StatusDisplay.print_success("API key saved successfully")
        else:
            StatusDisplay.print_error("Failed to save API key")
            return 1
        
        # If only saving API key, exit here
        if not args.folder_path:
            return 0
    
    # Validate folder path
    if not args.folder_path:
        parser.error("folder_path is required unless using --save-api-key only")
    
    folder_path = Path(args.folder_path)
    if not folder_path.exists():
        StatusDisplay.print_error(f"Folder not found: {folder_path}")
        return 1
    
    if not folder_path.is_dir():
        StatusDisplay.print_error(f"Path is not a directory: {folder_path}")
        return 1
    
    # Setup logging
    if not args.quiet:
        setup_logging(args.verbose)
    
    # Get API key (from argument or config)
    api_key = args.api_key
    if not api_key:
        config_manager = ConfigManager()
        api_key = config_manager.get_api_key()
        if not api_key:
            StatusDisplay.print_warning("No API key provided. Some features may be limited.")
    
    try:
        # Initialize processor
        processor = CivitaiProcessor(
            folder_path=str(folder_path),
            api_key=api_key,
            rate_limit_delay=args.rate_limit,
        )
        
        # Process directory
        results = processor.process_directory(download_images=args.img)
        
        if not results['success']:
            StatusDisplay.print_error(f"Sync failed: {results.get('error', 'Unknown error')}")
            return 1
            
    except KeyboardInterrupt:
        StatusDisplay.print_info("Interrupted by user")
        return 1
    except Exception as e:
        StatusDisplay.print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())