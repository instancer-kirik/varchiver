# Varchiver

A powerful cross-platform archive management tool with advanced features and modern UI.

Current version: 0.2.4

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

2. Install uv and dependencies:
```bash
pip install uv
uv pip install -e .[dev]
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

- Python 3.10+
- PyQt6
- uv (for building from source)
- unrar (for RAR support)

## License

Proprietary - All rights reserved

## Support the Project

Varchiver is an open-source project that relies on community support. If you find this tool useful, please consider supporting its development. You can find more details about how to contribute in our [funding.json](./funding.json) file.

To support the project directly, you can send Solana to the following address:
4zn9C2pgnxQwHvmoKCnyoV1YLtYFX5qxSaTxE2T86JEq
`4zn9C2pgnxQwHvmoKCnyoV1YLtYFX5qxSaTxE2T86JEq`

Your support helps ensure the continued development and maintenance of Varchiver. Thank you!
