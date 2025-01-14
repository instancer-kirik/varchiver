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
    'python-build'
    'python-installer'
    'python-wheel'
    'python-pip'
    'python-pyinstaller'
)
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('b91cab8d31cfb9f4166f89fb8e87bd758c633965f8245f49ffbc9e319ca8a372')

build() {
    cd "$pkgname-$pkgver"
    uv pip install --system --no-deps .
}

package() {
    cd "$pkgname-$pkgver"
    uv pip pyinstaller --clean --onefile --name varchiver varchiver/main.py
    python -m installer --destdir="$pkgdir" dist/*.whl
    
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
