"""Pattern matching utilities for file and path matching."""

import fnmatch
from pathlib import Path
from typing import List, Set

def should_skip_file(filepath: str, skip_patterns: List[str]) -> bool:
    """
    Check if a file should be skipped based on patterns.
    Handles various pattern types including directory patterns.
    """
    if not skip_patterns:
        return False
        
    filepath = str(filepath)  # Convert Path objects to string
    
    for pattern in skip_patterns:
        if pattern.startswith('**/'):
            # Match anywhere in path
            if fnmatch.fnmatch(filepath, pattern[3:]):
                return True
        elif pattern.endswith('/**'):
            # Match directory and all contents
            dir_pattern = pattern[:-3]
            path_parts = Path(filepath).parts
            for i in range(len(path_parts)):
                if fnmatch.fnmatch(str(Path(*path_parts[:i+1])), dir_pattern):
                    return True
        else:
            # Match from start of path
            if fnmatch.fnmatch(filepath.lower(), pattern.lower()):
                return True
    return False

def read_pattern_file(file_path: str, ignore_comments: bool = True) -> Set[str]:
    """
    Read patterns from a file (like .gitignore or .gitattributes).
    Returns a set of non-empty patterns.
    """
    patterns = set()
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and (not ignore_comments or not line.startswith('#')):
                    patterns.add(line)
    except Exception:
        pass
    return patterns

def pattern_matches(pattern: str, test_str: str) -> bool:
    """
    Check if a pattern matches a test string.
    Handles glob patterns with proper regex conversion.
    """
    # Convert glob pattern to regex
    regex = pattern.replace('.', r'\.')
    regex = regex.replace('*', '.*')
    regex = regex.replace('?', '.')
    regex = f"^{regex}$"
    
    import re
    try:
        return bool(re.match(regex, test_str))
    except re.error:
        return False