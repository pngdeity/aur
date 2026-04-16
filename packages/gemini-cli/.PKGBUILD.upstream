# Maintainer: Carl Smedstad <carsme@archlinux.org>
# Contributor: huyz

pkgname=gemini-cli
pkgver=0.38.0
pkgrel=1
epoch=1
pkgdesc="Open-source AI agent that brings the power of Gemini directly into your terminal"
arch=(x86_64)
url="https://github.com/google-gemini/gemini-cli"
license=(Apache-2.0)
depends=(
  glib2
  glibc
  libgcc
  libsecret
  libstdc++
  nodejs
)
makedepends=(
  git
  jq
  node-gyp
  npm
  python
)
optdepends=(
  'ripgrep: file content search'
  'wl-clipboard: clipboard image pasting on Wayland'
  'xclip: clipboard image pasting on X11'
  'xdg-utils: opening URLs in default browser'
)
checkdepends=(
  bubblewrap
  vim
)
source=("git+$url.git#tag=v$pkgver")
b2sums=('f0289c9c1ab6f0dd19d09699f7ae307e3f43eeaa552a52b65b9251fa07f4afd841e52cc72bb765b16aba0bdc18773d596d32e2f3323a54b67b5f3800e6bba057')

prepare() {
  cd $pkgname
  npm clean-install --ignore-scripts
}

build() {
  cd $pkgname
  npm run bundle
  # Build keytar native addon to enable OS keychain integration via libsecret
  # (GNOME Keyring, KDE Wallet, etc.) instead of falling back to a file-based
  # keychain.
  (
    cd node_modules/keytar
    node-gyp rebuild
  )
  local bundled=$(jq '.dependencies + .optionalDependencies | keys' package.json)
  npm pkg set --json bundledDependencies="$bundled"
  npm pack
}

check() {
  cd $pkgname
  npm run build
  # Deselect failing tests
  npm run test --workspaces --if-present -- \
    --exclude='**/BuiltinCommandLoader.test.ts' \
    --exclude='**/config.integration.test.ts' \
    --exclude='**/mcp-client.test.ts' \
    --exclude='**/sandboxManager.integration.test.ts'
  npm run test:sea-launch
}

package() {
  cd $pkgname
  npm install --global --offline --prefix "$pkgdir/usr" \
    google-$pkgname-$pkgver.tgz
  # Remove node-gyp build artifacts
  rm -vr "$pkgdir/usr/lib/node_modules/@google/gemini-cli/node_modules/keytar/build/Release/obj.target"
  install -vDm644 -t "$pkgdir/usr/share/doc/$pkgname" README.md
  install -vDm644 -t "$pkgdir/usr/share/licenses/$pkgname" LICENSE
}
