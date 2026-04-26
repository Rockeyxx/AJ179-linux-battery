#!/bin/bash

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Fatal: Uninstallation requires elevated privileges. Run as root (sudo ./uninstall.sh)."
  exit 1
fi

echo "Executing state teardown..."
systemctl disable --now ajazz-mouse.service || true



echo "Uninstalling static files via Makefile..."
if [ -f Makefile ]; then
    make uninstall
else
    echo "Makefile not found, attempting manual fallback cleanup..."
    rm -f /usr/local/bin/ajazz_daemon
    rm -f /etc/systemd/system/ajazz-mouse.service
    rm -f /etc/udev/rules.d/99-ajazz.rules
    rm -f /etc/conf.d/ajazz-battery
fi

echo "Executing final state reset..."
systemctl daemon-reload
udevadm control --reload-rules

echo "Uninstallation complete!"
