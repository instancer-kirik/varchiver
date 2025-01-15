# Maintainer: instancer-kirik
pkgname=varchiver
pkgver=0.4.5
pkgrel=1
pkgdesc="A variable archiver and github/aur release manager (serialize your variables first)"
arch=('x86_64')
url="https://github.com/instancer-kirik/varchiver"
license=('GPL3')
depends=(
    'python'
    'python-pyqt6'
    'python-pyqt6-webengine'
    'python-uv'
)
makedepends=(
    'python-build'
    'python-installer'
    'python-wheel'
    'python-pip'
)

# For AUR releases, use the GitHub source
if [ -z "$VARCHIVER_LOCAL_BUILD" ]; then
    source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
    sha256sums=('SKIP')  # Will be updated by release manager
else
    source=()
    sha256sums=()
fi

build() {
    # Use source directory for AUR builds, project root for local builds
    if [ -z "$VARCHIVER_LOCAL_BUILD" ]; then
        cd "$srcdir/$pkgname-$pkgver"
    else
        cd "$startdir"
    fi
    
    # Clean up any existing virtual environment
    rm -rf .venv
    
    # Create and activate virtual environment
    python -m venv .venv
    source .venv/bin/activate
    
    # Install dependencies and build
    if [ -f "pyproject.toml" ]; then
        # Use pip/uv if pyproject.toml exists
        if command -v uv &> /dev/null; then
            uv pip install .
            uv pip install pyinstaller
        else
            pip install .
            pip install pyinstaller
        fi
    elif [ -f "setup.py" ]; then
        # Use setup.py if it exists
        pip install .
        pip install pyinstaller
    elif [ -f "requirements.txt" ]; then
        # Fall back to requirements.txt
        pip install -r requirements.txt
        pip install .
        pip install pyinstaller
    fi
    
    # Build executable
    python -m PyInstaller --clean --onefile --name varchiver bootstrap.py
    
    # Deactivate virtual environment
    deactivate
}

package() {
    # Use source directory for AUR builds, project root for local builds
    if [ -z "$VARCHIVER_LOCAL_BUILD" ]; then
        cd "$srcdir/$pkgname-$pkgver"
    else
        cd "$startdir"
    fi
    
    # Install executable
    install -Dm755 dist/varchiver "$pkgdir/usr/bin/varchiver"
    
    # Install desktop file and icon
    install -Dm644 varchiver.desktop "$pkgdir/usr/share/applications/varchiver.desktop"
    install -Dm644 varchiver.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/varchiver.svg"
    
    # Install license and readme
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}

# Get version from PKGBUILD
get_version() {
    grep '^pkgver=' PKGBUILD | cut -d'=' -f2
}

# Force rebuild during release
force_rebuild() {
    rm -rf pkg/ dist/ *.pkg.tar.zst
    VARCHIVER_LOCAL_BUILD=1 makepkg -f --noconfirm --skipchecksums
}
