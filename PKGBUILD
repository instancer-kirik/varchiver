# Maintainer: kirik
pkgname=varchiver
pkgver=0.3.6
pkgrel=1
pkgdesc="Advanced Archive Management Tool with modern UI"
arch=('any')
url="https://github.com/instancer-kirik/varchiver"
license=('custom:proprietary')
depends=(
    'python'
    'python-pyqt6'
    'python-psutil'
    'p7zip'
    'rar'
)
makedepends=(
    'uv'
)
# Build from parent directory
source=()
sha256sums=()

build() {
    cd ..
    # Create and activate virtual environment
    uv venv .venv
    export VIRTUAL_ENV="$PWD/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"
    unset PYTHONHOME
    
    # Install uv in the virtual environment
    python -m pip install uv
    
    # Install dependencies
    uv pip install pyinstaller
    uv pip install .
    
    # Run pyinstaller
    python -m pyinstaller --clean \
        --onefile \
        --name varchiver \
        --hidden-import PyQt6 \
        --hidden-import rarfile \
        --hidden-import varchiver \
        --collect-submodules varchiver \
        varchiver/bootstrap.py
}

package() {
    cd ..
    # Install the binary
    install -Dm755 "dist/varchiver" "$pkgdir/usr/bin/varchiver"
    
    # Install desktop file
    install -Dm644 "varchiver.desktop" \
        "$pkgdir/usr/share/applications/$pkgname.desktop"

    # Install icon
    install -Dm644 "varchiver.svg" \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps/$pkgname.svg"

    # Install license
    install -Dm644 "LICENSE" \
        "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}

# Get version from PKGBUILD
get_version() {
    grep '^pkgver=' PKGBUILD | cut -d'=' -f2
}
