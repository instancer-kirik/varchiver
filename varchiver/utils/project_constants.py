"""Project-specific constants and configurations."""
import re
from pathlib import Path

def get_version_from_pkgbuild() -> str:
    """Get version from PKGBUILD file."""
    try:
        pkgbuild_path = Path(__file__).resolve().parent.parent.parent / 'PKGBUILD'
        if not pkgbuild_path.exists():
            return '0.0.0'  # Fallback version if PKGBUILD not found
            
        content = pkgbuild_path.read_text()
        match = re.search(r'^pkgver=([0-9][0-9a-z.-]*)$', content, re.MULTILINE)
        if match:
            return match.group(1)
        return '0.0.0'  # Fallback version if version not found
    except Exception:
        return '0.0.0'  # Fallback version if any error occurs

# Project-wide constants
PROJECT_NAME = 'Varchiver'
PROJECT_VERSION = get_version_from_pkgbuild()

# Project type configurations
PROJECT_CONFIGS = {
    "Python": {
        "files": "pyproject.toml,PKGBUILD",
        "patterns": 'version = "*",pkgver=*,version="*"',
        "build": "makepkg -f"
    },
    "Node.js": {
        "files": "package.json",
        "patterns": '"version": "*"',
        "build": "npm run build"
    },
    "Rust": {
        "files": "Cargo.toml",
        "patterns": 'version = "*"',
        "build": "cargo build --release"
    },
    "Go": {
        "files": "go.mod",
        "patterns": 'v*',
        "build": "go build"
    },
    # Application config
    "name": PROJECT_NAME,
    "version": PROJECT_VERSION
}

# Common Git export-ignore patterns with descriptions, grouped by category
GIT_EXPORT_PATTERNS = [
    # Build artifacts
    ("# Build artifacts", None),
    ("*.tar.gz export-ignore", "Distribution archives - usually excluded from releases"),
    ("*.pkg.tar.zst export-ignore", "Arch package files - usually excluded from releases"),
    ("dist/ export-ignore", "Distribution directory - usually excluded from releases"),
    ("build/ export-ignore", "Build artifacts directory - usually excluded from releases"),
    
    # Development environment
    ("# Development environment", None),
    ("__pycache__/ export-ignore", "Python cache files - safe to exclude"),
    ("*.pyc export-ignore", "Compiled Python files - safe to exclude"),
    (".venv/ export-ignore", "Python virtual environment - safe to exclude"),
    ("node_modules/ export-ignore", "Node.js dependencies - safe to exclude"),
    
    # IDE and editor files
    ("# IDE and editor files", None),
    (".vscode/ export-ignore", "VS Code settings - safe to exclude"),
    (".idea/ export-ignore", "IntelliJ settings - safe to exclude"),
    ("*.swp export-ignore", "Vim swap files - safe to exclude"),
    ("*.swo export-ignore", "Vim swap files - safe to exclude"),
    (".DS_Store export-ignore", "macOS system files - safe to exclude"),
    
    # Project-specific (unchecked by default)
    ("# Project-specific files", None),
    ("src/ export-ignore", "Source directory - CAUTION: only exclude if not needed in releases", False),
    ("pkg/ export-ignore", "Package build directory - project specific", False),
    ("tests/ export-ignore", "Test files - project specific", False),
    ("docs/ export-ignore", "Documentation source - project specific", False),
    
    # Sensitive files (checked by default)
    ("# Sensitive files", None),
    (".env export-ignore", "Environment files - recommended to exclude if containing secrets", True),
    (".env.* export-ignore", "Environment files - recommended to exclude if containing secrets", True),
    ("*.key export-ignore", "Key files - recommended to exclude", True),
    ("*.pem export-ignore", "Certificate files - recommended to exclude", True)
]

# Sensitive patterns that should be in .gitignore
SENSITIVE_PATTERNS = {
    '.env',
    '*.env',
    '.env.*',
    'env/',
    '.env.local',
    '.env.*.local',
    '*.pem',
    '*.key',
    'id_rsa',
    'id_dsa',
    '*.pfx',
    '*.p12',
    '*.keystore',
    'secrets.*',
    '*password*',
    '*secret*',
    '*credential*',
    '.aws/',
    '.ssh/',
}

# Common patterns to skip during archiving
DEFAULT_SKIP_PATTERNS = {
    'build': ['_build', 'build', 'dist', 'target', '*/_build', '*/build', '*/dist', '*/target'],
    'deps': ['deps', 'node_modules', 'venv', '.venv', '__pycache__', 'vendor', '*/deps', '*/deps/*', '**/deps/**', '**/node_modules/**', '**/venv/**', '**/.venv/**', '**/__pycache__/**', '**/vendor/**'],
    'ide': ['.idea', '.vscode', '*.pyc', '*.pyo', '*.pyd', '.DS_Store', '**/.idea/**', '**/.vscode/**', '**/*.pyc', '**/*.pyo', '**/*.pyd', '**/.DS_Store'],
    'git': ['.git', '.gitignore', '.gitmodules', '.gitattributes', '**/.git/**', '**/.gitignore', '**/.gitmodules', '**/.gitattributes'],
    'elixir': ['_build', 'deps', '.elixir_ls', '.fetch', '**/_build/**', '**/deps/**', '**/.elixir_ls/**', '**/.fetch/**'],
    'logs': ['*.log', 'logs', '*.dump', '**/*.log', '**/logs/**', '**/*.dump'],
    'tmp': ['tmp', '*.tmp', '*.bak', '*.swp', '**/tmp/**', '**/*.tmp', '**/*.bak', '**/*.swp']
}

# Archive extensions and their display names
ARCHIVE_EXTENSIONS = {
    "Archives (*.zip)": ".zip",
    "TAR Archives (*.tar)": ".tar", 
    "Gzipped TAR Archives (*.tar.gz)": ".tar.gz",
    "TGZ Archives (*.tgz)": ".tgz",
    "Bzip2 TAR Archives (*.tar.bz2)": ".tar.bz2",
    "7z Archives (*.7z)": ".7z",
    "RAR Archives (*.rar)": ".rar"
}