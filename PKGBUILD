# Maintainer: instancer-kirik
pkgname=varchiver
pkgver=0.4.9
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
    'python-psutil'
    'git'  # Required for git operations
    'github-cli'  # Required for GitHub releases
    'ttf-dejavu'  # Required for icons/glyphs
    'libnotify'   # Required for notifications
)
makedepends=(
    'python-build'
    'python-installer'
    'python-wheel'
    'python-pip'
    'python-pyinstaller'
)
optdepends=(
    'python-rarfile: for RAR archive support'
)
source=("varchiver-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=("008b04f30aa647aca570439e8f1a57f9b780824948ff710eff517a6e9b7c7b04")  # Will be updated by release manager

build() {
    cd "$srcdir/$pkgname-$pkgver"
    
    # Clean up any existing virtual environment
    rm -rf .venv
    
    # Create and activate virtual environment
    python -m venv .venv
    source .venv/bin/activate
    
    # Install in development mode
    pip install -e .
    
    # Build executable with explicit module includes
    pyinstaller --clean --onefile --name varchiver \
        --hidden-import varchiver \
        --hidden-import varchiver.utils \
        --hidden-import varchiver.threads \
        --hidden-import varchiver.widgets \
        --add-data "varchiver/resources:varchiver/resources" \
        --add-data "varchiver/widgets:varchiver/widgets" \
        bootstrap.py
    
    # Deactivate virtual environment
    deactivate
}

package() {
    cd "$srcdir/$pkgname-$pkgver"
    
    # Create necessary directories
    install -dm755 "$pkgdir/usr/share/$pkgname"
    
    # Install executable
    install -Dm755 dist/varchiver "$pkgdir/usr/bin/varchiver"
    
    # Install desktop file and icon
    install -Dm644 varchiver.desktop "$pkgdir/usr/share/applications/varchiver.desktop"
    install -Dm644 resources/icons/archive.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/varchiver.svg"
    
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
    makepkg -f --noconfirm
}
