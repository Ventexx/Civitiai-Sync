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
    """Handles status messages and progress display"""
    
    @staticmethod
    def print_header(message: str):
        """Print a header message"""
        print(f"\n🚀 {message}")
    
    @staticmethod
    def print_success(message: str):
        """Print a success message"""
        print(f"✅ {message}")
    
    @staticmethod
    def print_warning(message: str):
        """Print a warning message"""
        print(f"⚠️  {message}")
    
    @staticmethod
    def print_error(message: str):
        """Print an error message"""
        print(f"❌ {message}", file=sys.stderr)
    
    @staticmethod
    def print_info(message: str):
        """Print an info message"""
        print(f"ℹ️  {message}")
    
    @staticmethod
    def print_results(stats: dict):
        """Print processing results"""
        print(f"\n✅ Sync completed successfully!")
        print(f"   📁 Total files: {stats['total_files']}")
        print(f"   🧮 Hashes computed: {stats['hashes_computed']}")
        print(f"   📊 Metadata fetched: {stats['metadata_fetched']}")
        print(f"   💾 Files saved: {stats['files_saved']}")
        
        if 'images_downloaded' in stats:
            print(f"   🖼️  Images downloaded: {stats['images_downloaded']}")
        
        if stats.get('errors'):
            print(f"   ⚠️  Errors: {len(stats['errors'])}")