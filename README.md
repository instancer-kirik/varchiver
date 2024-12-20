# Varchiver

A powerful cross-platform archive management tool with advanced features and modern UI.

## Features

- Support for multiple archive formats:
  - ZIP archives (*.zip)
  - TAR archives (*.tar)
  - Gzipped TAR (*.tar.gz, *.tgz)
  - Bzip2 TAR (*.tar.bz2)
  - RAR archives (*.rar)
 
- Advanced capabilities:
  - Password protection (ZIP, RAR)
  - Smart collision handling
  - Configurable skip patterns
  - Permission preservation
  - Git permissions fixing
  - Progress tracking
  - Detailed error messages
  - TAR indexing for faster subsequent loading

## Installation

### From Binary Release

1. Download the latest release:
```bash
wget https://github.com/kirik/varchiver/releases/latest/download/varchiver-linux-x86_64.tar.gz
```

2. Extract and install:
```bash
tar xzf varchiver-linux-x86_64.tar.gz
sudo mv varchiver /usr/local/bin/
```

### From AUR (Arch Linux)

1. Install using yay:
```bash
yay -S varchiver
```

### From Source

1. Clone the repository:
```bash
git clone https://github.com/kirik/varchiver.git
cd varchiver
```

2. Install dependencies:
```bash
poetry install
```

3. Build:
```bash
./build.sh
```

The binary will be available in `dist/varchiver-linux-x86_64.tar.gz`

## Usage

1. Launch Varchiver:
```bash
varchiver
```

2. Use the GUI to:
   - Browse archive contents
   - Create new archives
   - Extract files
   - Manage file permissions

## Requirements

- Python 3.10
- PyQt6
- Poetry (for building from source)
- unrar (for RAR support)

## License

Proprietary - All rights reserved
