import sys
import time
from typing import Optional


class ProgressBar:
    """Simple progress bar for terminal output."""
    
    def __init__(self, total: int, description: str = "", width: int = 50, single_line: bool = False):
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.start_time = time.time()
        self.last_update_time = 0
        self.single_line = single_line
        self.description_printed = False
        
    def update(self, current: Optional[int] = None, description: Optional[str] = None):
        """Update progress bar."""
        if current is not None:
            self.current = current
        else:
            self.current += 1
            
        if description is not None:
            self.description = description
            
        # Throttle updates to avoid too frequent refreshes (except for single_line mode)
        current_time = time.time()
        if not self.single_line and current_time - self.last_update_time < 0.1 and self.current < self.total:
            return
        self.last_update_time = current_time
            
        self._draw()
    
    def _draw(self):
        """Draw the progress bar."""
        if self.total == 0:
            return
            
        # Calculate progress
        progress = min(self.current / self.total, 1.0)
        filled_width = int(self.width * progress)
        
        # Create progress bar
        filled_char = '█'
        empty_char = '─'
        bar = filled_char * filled_width + empty_char * (self.width - filled_width)
        
        # Calculate percentage
        percentage = progress * 100
        
        # Calculate elapsed time and ETA
        elapsed = time.time() - self.start_time
        if self.current > 0 and self.current < self.total:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f" ETA: {self._format_time(eta)}"
        else:
            eta_str = ""
        
        if self.single_line:
            # Single-line mode for hashing
            if not self.description_printed:
                print(f"{self.description}")
                self.description_printed = True
            
            # Build the progress line
            line = f"({self.current}/{self.total}) [{bar}] {percentage:.1f}%{eta_str}"
            
            # Clear the line by padding with spaces, then use carriage return
            terminal_width = 120
            line_padded = line.ljust(terminal_width)
            print(f"\r{line_padded}", end='', flush=True)
            
            if self.current == self.total:
                print()
        else:
            # Multi-line mode for metadata fetching
            line = f"{self.description}\n({self.current}/{self.total}) [{bar}] {percentage:.1f}%{eta_str}"
            print(line, flush=True)

    @staticmethod
    def print_results(stats: dict):
        """Print processing results in a clean format."""
        total_time = StatusDisplay.get_elapsed_time()
    
        print(f"\n┌─ Sync completed in {total_time}")
        print(f"│ 📁 Files processed: {stats['total_files']}")
    
        # Show detailed stats
        details = []
        if stats.get('hashes_computed', 0) > 0:
            details.append(f"🔢 Hashes computed: {stats['hashes_computed']}")
    
        if stats.get('metadata_fetched', 0) > 0:
            details.append(f"📋 Metadata fetched: {stats['metadata_fetched']}")
    
        if stats.get('files_saved', 0) > 0:
            details.append(f"💾 Files saved: {stats['files_saved']}")
    
        if stats.get('images_downloaded', 0) > 0:
            details.append(f"🖼️ Images downloaded: {stats['images_downloaded']}")
    
        if stats.get('not_found', 0) > 0:
            details.append(f"❌ Not found on Civitai: {stats['not_found']}")
    
        for detail in details:
            print(f"│ {detail}")
    
        if stats.get('errors') and len(stats['errors']) > 0:
            print(f"│ ⚠ Errors encountered: {len(stats['errors'])}")
    
        print("└─")
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds//60:.0f}m {seconds%60:.0f}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"
    
    def finish(self, description: Optional[str] = None):
        """Mark progress as complete."""
        if self.single_line:
            # For single-line mode, just print completion message on new line
            if description:
                print(description)
        else:
            # For multi-line mode, update to 100%
            if description:
                self.description = description
            self.update(self.total)

class StatusDisplay:
    """Handles status messages and progress display with timing information."""
    
    _start_time = None
    
    @classmethod
    def start_timing(cls):
        """Start timing for the entire process."""
        cls._start_time = time.time()
    
    @classmethod
    def get_elapsed_time(cls) -> str:
        """Get formatted elapsed time since start."""
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
        """Get current timestamp with elapsed time in brackets."""
        current_time = time.strftime("%H:%M:%S")
        elapsed = cls.get_elapsed_time()
        return f"{current_time} ({elapsed})"
    
    @classmethod
    def _clean_logger_name(cls, name: str) -> str:
        """Remove civitai_sync prefix from logger names."""
        if name.startswith('civitai_sync.'):
            return name[13:]
        return name
    
    @staticmethod
    def print_header(message: str):
        """Print a header message."""
        StatusDisplay.start_timing()
        print(f"\n┌─ {message}")
    
    @staticmethod
    def print_success(message: str):
        """Print a success message."""
        timestamp = StatusDisplay._get_timestamp_with_elapsed()
        print(f"{timestamp} ✓ {message}")
    
    @staticmethod
    def print_warning(message: str):
        """Print a warning message."""
        timestamp = StatusDisplay._get_timestamp_with_elapsed()
        print(f"{timestamp} ⚠ {message}")
    
    @staticmethod
    def print_error(message: str):
        """Print an error message."""
        timestamp = StatusDisplay._get_timestamp_with_elapsed()
        print(f"{timestamp} ✗ {message}", file=sys.stderr)
    
    @staticmethod
    def print_info(message: str):
        """Print an info message."""
        timestamp = StatusDisplay._get_timestamp_with_elapsed()
        print(f"{timestamp} · {message}")
    
    @staticmethod
    def print_results(stats: dict):
        """Print processing results."""
        total_time = StatusDisplay.get_elapsed_time()
        
        print(f"\n┌─ Sync completed in {total_time}")
        print(f"│ Files processed: {stats['total_files']}")
        
        details = []
        if stats.get('hashes_computed', 0) > 0:
            details.append(f"Hashes computed: {stats['hashes_computed']}")
        
        if stats.get('metadata_fetched', 0) > 0:
            details.append(f"Metadata fetched: {stats['metadata_fetched']}")
        
        if stats.get('files_saved', 0) > 0:
            details.append(f"Files saved: {stats['files_saved']}")
        
        if stats.get('images_downloaded', 0) > 0:
            details.append(f"Images downloaded: {stats['images_downloaded']}")
        
        if stats.get('not_found', 0) > 0:
            details.append(f"Not found on Civitai: {stats['not_found']}")
        
        for detail in details:
            print(f"│ {detail}")
        
        if stats.get('errors') and len(stats['errors']) > 0:
            print(f"│ Errors encountered: {len(stats['errors'])}")
        
        print("└─")
    
    @staticmethod
    def setup_logging_formatter():
        """Setup custom logging formatter for cleaner display."""
        import logging
        
        class CustomFormatter(logging.Formatter):
            def format(self, record):
                timestamp = StatusDisplay._get_timestamp_with_elapsed()
                logger_name = StatusDisplay._clean_logger_name(record.name)
                level = record.levelname
                message = record.getMessage()
                
                # Use simple symbols for different log levels
                level_symbols = {
                    'INFO': '·',
                    'WARNING': '⚠',
                    'ERROR': '✗',
                    'DEBUG': '·',
                    'CRITICAL': '✗'
                }
                
                symbol = level_symbols.get(level, '·')
                
                # Only show logger name for non-INFO levels or when it's not the main module
                if level != 'INFO' or logger_name not in ['civitai_processor', 'file_manager']:
                    return f"{timestamp} {symbol} {logger_name} - {message}"
                else:
                    return f"{timestamp} {symbol} {message}"
        
        # Apply the custom formatter to all handlers
        logger = logging.getLogger()
        for handler in logger.handlers:
            handler.setFormatter(CustomFormatter())