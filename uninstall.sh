#!/bin/bash
# Removes what install.sh installed: the battery service, ajazzctl and the AJ179 app.
# Works from a clone or on its own (curl -fsSL …/uninstall.sh | sudo bash).
# Your saved button map and macros in ~/.config/ajazzctl are left alone.

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Run as root: sudo bash uninstall.sh (or pipe it to sudo bash)." >&2
  exit 1
fi

systemctl disable --now ajazz-mouse.service 2>/dev/null || true

# The files `make install` puts in place (PREFIX=/usr), plus old locations.
rm -f /usr/bin/ajazz_daemon /usr/bin/ajazzctl /usr/bin/aj179 \
  /usr/share/man/man1/ajazzctl.1 \
  /etc/systemd/system/ajazz-mouse.service \
  /etc/conf.d/ajazz-battery \
  /etc/udev/rules.d/70-ajazz.rules /etc/udev/rules.d/99-ajazz.rules \
  /usr/share/applications/aj179.desktop \
  /usr/share/icons/hicolor/scalable/apps/aj179.svg \
  /usr/local/bin/ajazz_daemon
rm -rf /usr/share/aj179-linux

systemctl daemon-reload
udevadm control --reload-rules
echo "Removed aj179-linux."
