#!/usr/bin/env python3
"""
Civitai Sync - CLI tool for syncing safetensor model metadata and images from Civitai
"""

import argparse
import sys
import logging
from pathlib import Path

from src.civitai_processor import CivitaiProcessor
from src.config_manager import ConfigManager


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def save_api_key(api_key: str) -> bool:
    """Save API key to config"""
    config_manager = ConfigManager()
    return config_manager.save_api_key(api_key)


def main():
    parser = argparse.ArgumentParser(
        description='Sync safetensor model metadata and images from Civitai',
        prog='civitai-sync'
    )
    
    # Main command - folder path
    parser.add_argument(
        'folder_path',
        nargs='?',
        help='Path to folder containing safetensor files'
    )
    
    # API key options
    parser.add_argument(
        '--api-key',
        help='Civitai API key for this session'
    )
    
    parser.add_argument(
        '--save-api-key',
        metavar='API_KEY',
        help='Save API key to local config for future use'
    )
    
    # Processing options
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
        '--refresh-metadata',
        action='store_true',
        help='Refresh metadata even if it exists and is recent'
    )
    
    parser.add_argument(
        '--max-age',
        type=int,
        default=30,
        help='Maximum age of metadata in days before refresh (default: 30)'
    )
    
    # Logging options
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
            print("✓ API key saved successfully")
        else:
            print("✗ Failed to save API key", file=sys.stderr)
            return 1
        
        # If only saving API key, exit here
        if not args.folder_path:
            return 0
    
    # Validate folder path
    if not args.folder_path:
        parser.error("folder_path is required unless using --save-api-key only")
    
    folder_path = Path(args.folder_path)
    if not folder_path.exists():
        print(f"✗ Error: Folder not found: {folder_path}", file=sys.stderr)
        return 1
    
    if not folder_path.is_dir():
        print(f"✗ Error: Path is not a directory: {folder_path}", file=sys.stderr)
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
            print("⚠️  Warning: No API key provided. Some features may be limited.")
    
    try:
        # Initialize processor
        processor = CivitaiProcessor(
            folder_path=str(folder_path),
            api_key=api_key,
            rate_limit_delay=args.rate_limit,
            refresh_metadata=args.refresh_metadata,
            max_metadata_age_days=args.max_age
        )
        
        # Process directory
        print(f"🚀 Starting sync for: {folder_path}")
        results = processor.process_directory(download_images=args.img)
        
        # Print results
        if results['success']:
            stats = results['stats']
            print(f"\n✅ Sync completed successfully!")
            print(f"   📁 Total files: {stats['total_files']}")
            print(f"   🧮 Hashes computed: {stats['hashes_computed']}")
            print(f"   📊 Metadata fetched: {stats['metadata_fetched']}")
            print(f"   💾 Files saved: {stats['files_saved']}")
            
            if args.img and 'images_downloaded' in stats:
                print(f"   🖼️  Images downloaded: {stats['images_downloaded']}")
            
            if stats.get('errors'):
                print(f"   ⚠️  Errors: {len(stats['errors'])}")
                if args.verbose:
                    for error in stats['errors']:
                        print(f"      • {error}")
        else:
            print(f"❌ Sync failed: {results.get('error', 'Unknown error')}")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())