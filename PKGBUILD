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
# Local development source
source=("${pkgname}-${pkgver}"::"file://${PWD}")
sha256sums=('SKIP')

build() {
    cd "${pkgname}-${pkgver}"
    # Create virtual environment and install dependencies
    uv venv .venv
    source .venv/bin/activate
    # Install dependencies including PyInstaller
    uv pip install pyinstaller
    uv pip install --system --no-deps .
    # Run pyinstaller with the virtual environment's Python
    .venv/bin/python -m pyinstaller --clean \
        --onefile \
        --name varchiver \
        --hidden-import PyQt6 \
        --hidden-import rarfile \
        --hidden-import varchiver \
        --collect-submodules varchiver \
        varchiver/bootstrap.py
    deactivate
}

package() {
    cd "${pkgname}-${pkgver}"
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
