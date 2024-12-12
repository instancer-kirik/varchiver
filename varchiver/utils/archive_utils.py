import os

def get_archive_type(archive_path):
    """Helper method to determine archive type from file extension"""
    # Check if it's a directory first
    if os.path.isdir(archive_path):
        return 'dir'
        
    ext = os.path.splitext(archive_path.lower())[1]
    if ext in ('.gz', '.bz2', '.xz'):
        # Handle .tar.gz, .tar.bz2, etc.
        base = os.path.splitext(archive_path[:-len(ext)])[1]
        if base == '.tar':
            return base + ext
    return ext

def format_size(size):
    """Format size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        else:
            return f"{size/(1024*1024):.1f} MB"
