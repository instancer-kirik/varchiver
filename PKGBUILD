# Maintainer: kirik
pkgname=varchiver
pkgver=0.2.4
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
    'python-pyinstaller'
)
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('b91cab8d31cfb9f4166f89fb8e87bd758c633965f8245f49ffbc9e319ca8a372')

build() {
    cd "$pkgname-$pkgver"
    # Create virtual environment and install dependencies
    uv venv .venv
    source .venv/bin/activate
    # Install dependencies
    uv pip install --system pyinstaller
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
    cd "$pkgname-$pkgver"
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
