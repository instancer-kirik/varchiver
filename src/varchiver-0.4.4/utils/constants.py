# Common patterns to skip
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
