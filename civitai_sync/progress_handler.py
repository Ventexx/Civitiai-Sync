"""
Progress bar and visual feedback utilities for Civitai Sync
"""

import sys
import time
from typing import Optional


class ProgressBar:
    """Simple progress bar for terminal output"""
    
    def __init__(self, total: int, description: str = "", width: int = 50):
        """
        Initialize progress bar
        
        Args:
            total: Total number of items to process
            description: Description of current operation
            width: Width of the progress bar in characters
        """
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.start_time = time.time()
        self.last_update_time = 0
        
    def update(self, current: Optional[int] = None, description: Optional[str] = None):
        """
        Update progress bar
        
        Args:
            current: Current progress (if None, increments by 1)
            description: New description (if provided)
        """
        if current is not None:
            self.current = current
        else:
            self.current += 1
            
        if description is not None:
            self.description = description
            
        # Throttle updates to avoid too frequent refreshes
        current_time = time.time()
        if current_time - self.last_update_time < 0.1 and self.current < self.total:
            return
        self.last_update_time = current_time
            
        self._draw()
    
    def _draw(self):
        """Draw the progress bar"""
        if self.total == 0:
            return
            
        # Calculate progress
        progress = min(self.current / self.total, 1.0)
        filled_width = int(self.width * progress)
        
        # Create progress bar
        bar = '█' * filled_width + '░' * (self.width - filled_width)
        
        # Calculate percentage
        percentage = progress * 100
        
        # Calculate elapsed time and ETA
        elapsed = time.time() - self.start_time
        if self.current > 0 and self.current < self.total:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f" ETA: {self._format_time(eta)}"
        else:
            eta_str = ""
        
        # Format the line
        line = f"\r{self.description}\n({self.current}/{self.total}) [{bar}] {percentage:.1f}%{eta_str}"
        
        # Clear previous lines and write new content
        sys.stdout.write('\033[2K\033[1A\033[2K')  # Clear current and previous line
        sys.stdout.write(line)
        sys.stdout.flush()
        
        # Add newline when complete
        if self.current >= self.total:
            sys.stdout.write('\n')
            sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds//60:.0f}m {seconds%60:.0f}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"
    
    def finish(self, description: Optional[str] = None):
        """Mark progress as complete"""
        if description:
            self.description = description
        self.update(self.total)


class StatusDisplay:
    """Handles status messages and progress display with timing information"""
    
    _start_time = None
    
    @classmethod
    def start_timing(cls):
        """Start the global timing for the entire process"""
        cls._start_time = time.time()
    
    @classmethod
    def get_elapsed_time(cls) -> str:
        """Get formatted elapsed time since start"""
        if cls._start_time is None:
            return "0s"
        
        elapsed = time.time() - cls._start_time
        if elapsed < 60:
            return f"{elapsed:.0f}s"
        elif elapsed < 3600:
            return f"{elapsed//60:.0f}m {elapsed%60:.0f}s"
        else:
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"
    
    @classmethod
    def _get_timestamp_with_elapsed(cls) -> str:
        """Get current timestamp with elapsed time in brackets"""
        current_time = time.strftime("%H:%M:%S")
        elapsed = cls.get_elapsed_time()
        return f"{current_time} ({elapsed})"
    
    @classmethod
    def _clean_logger_name(cls, name: str) -> str:
        """Remove civitai_sync prefix from logger names"""
        if name.startswith('civitai_sync.'):
            return name[13:]  # Remove 'civitai_sync.' prefix
        return name
    
    @staticmethod
    def print_header(message: str):
        """Print a header message and start timing"""
        StatusDisplay.start_timing()
        print(f"\n→ {message}")
    
    @staticmethod
    def print_success(message: str):
        """Print a success message with timestamp"""
        timestamp = StatusDisplay._get_timestamp_with_elapsed()
        print(f"{timestamp} - SUCCESS - {message}")
    
    @staticmethod
    def print_warning(message: str):
        """Print a warning message with timestamp"""
        timestamp = StatusDisplay._get_timestamp_with_elapsed()
        print(f"{timestamp} - WARNING - {message}")
    
    @staticmethod
    def print_error(message: str):
        """Print an error message with timestamp"""
        timestamp = StatusDisplay._get_timestamp_with_elapsed()
        print(f"{timestamp} - ERROR - {message}", file=sys.stderr)
    
    @staticmethod
    def print_info(message: str):
        """Print an info message with timestamp"""
        timestamp = StatusDisplay._get_timestamp_with_elapsed()
        print(f"{timestamp} - INFO - {message}")
    
    @staticmethod
    def print_results(stats: dict):
        """Print processing results in a clean, minimal format"""
        total_time = StatusDisplay.get_elapsed_time()
        
        print(f"\nSync completed in {total_time}")
        print(f"Files processed: {stats['total_files']}")
        
        if stats.get('hashes_computed', 0) > 0:
            print(f"Hashes computed: {stats['hashes_computed']}")
        
        if stats.get('metadata_fetched', 0) > 0:
            print(f"Metadata fetched: {stats['metadata_fetched']}")
        
        if stats.get('files_saved', 0) > 0:
            print(f"Files saved: {stats['files_saved']}")
        
        if stats.get('images_downloaded', 0) > 0:
            print(f"Images downloaded: {stats['images_downloaded']}")
        
        if stats.get('not_found', 0) > 0:
            print(f"Not found on Civitai: {stats['not_found']}")
        
        if stats.get('errors') and len(stats['errors']) > 0:
            print(f"Errors encountered: {len(stats['errors'])}")
    
    @staticmethod
    def setup_logging_formatter():
        """Setup custom logging formatter for better display"""
        import logging
        
        class CustomFormatter(logging.Formatter):
            def format(self, record):
                timestamp = StatusDisplay._get_timestamp_with_elapsed()
                logger_name = StatusDisplay._clean_logger_name(record.name)
                level = record.levelname
                message = record.getMessage()
                
                return f"{timestamp} - {logger_name} - {level} - {message}"
        
        # Apply the custom formatter to all handlers
        logger = logging.getLogger()
        for handler in logger.handlers:
            handler.setFormatter(CustomFormatter())