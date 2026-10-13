#!/bin/bash
# Installs aj179-linux: the battery service, ajazzctl and the AJ179 desktop app.
#
#   One command:  curl -fsSL https://raw.githubusercontent.com/Rockeyxx/aj179-linux/main/install.sh | sudo bash
#   One file:     sudo bash install.sh      (downloads the rest)
#   In a clone:   sudo ./install.sh
#
# Another mouse's receiver: sudo VENDOR_ID=xxxx PRODUCT_ID=xxxx bash install.sh
# Running it again updates an existing install.

set -euo pipefail

REPO=https://github.com/Rockeyxx/aj179-linux
REF=${AJ179_REF:-main} # branch to download when not run from a clone

if [ "$EUID" -ne 0 ]; then
  echo "Run as root: sudo bash install.sh (or pipe it to sudo bash)." >&2
  exit 1
fi

echo "==> Installing dependencies"
if command -v pacman >/dev/null; then
  pacman -S --needed --noconfirm gcc make curl python-pyqt6 libnotify
elif command -v apt-get >/dev/null; then
  apt-get update
  apt-get install -y gcc make curl python3-pyqt6 libnotify-bin
elif command -v dnf >/dev/null; then
  dnf install -y gcc make curl python3-pyqt6 libnotify
else
  echo "Unknown package manager: install gcc, make and PyQt6 for Python 3 yourself." >&2
fi

# Use this clone if the script is in one; otherwise (piped from curl, or downloaded on
# its own) fetch the source. No prompts: when piped, stdin is the script itself.
here=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)
if [ -n "$here" ] && [ -f "$here/src/ajazzctl.c" ]; then
  src=$here
else
  src=$(mktemp -d)
  trap 'rm -rf "$src"' EXIT
  echo "==> Downloading aj179-linux ($REF)"
  curl -fsSL "$REPO/archive/refs/heads/$REF.tar.gz" | tar -xz -C "$src" --strip-components=1
fi
cd "$src"

echo "==> Building"
if [ "$src" = "$here" ] && [ -n "${SUDO_USER:-}" ]; then
  sudo -u "$SUDO_USER" make clean all # keep the clone's files owned by its user
else
  make clean all
fi

echo "==> Installing"
make install
if [ -n "${VENDOR_ID:-}" ] && [ -n "${PRODUCT_ID:-}" ]; then
  printf 'VENDOR_ID=%s\nPRODUCT_ID=%s\n' "$VENDOR_ID" "$PRODUCT_ID" >/etc/conf.d/ajazz-battery
fi

echo "==> Starting the battery service"
udevadm control --reload-rules && udevadm trigger
systemctl daemon-reload
systemctl enable ajazz-mouse.service
systemctl restart ajazz-mouse.service # an update runs the new daemon
systemctl --global enable aj179-battery-alert.service # low-battery notification, every user
if [ -n "${SUDO_USER:-}" ]; then # start it now for whoever ran this, not just at next login
  systemctl --user -M "$SUDO_USER@" restart aj179-battery-alert.service 2>/dev/null || true
fi

echo
echo "Done. Open \"AJ179\" from your application launcher (or run: aj179)."
echo "Command line: ajazzctl (see: man ajazzctl). Battery level: /tmp/ajazz_battery"
