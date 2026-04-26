#!/bin/bash

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Fatal: Deployment requires elevated privileges. Run as root (sudo ./install.sh)."
  exit 1
fi

echo "Detecting package manager to install dependencies..."
if command -v pacman &> /dev/null; then
    echo "Arch Linux detected. Installing dependencies..."
    pacman -S --needed libusb gcc make
elif command -v apt &> /dev/null; then
    echo "APT-based distribution detected. Installing dependencies..."
    apt update
    apt install -y libusb-1.0-0-dev gcc make
else
    echo "Warning: Unsupported package manager. Please install libusb, make, and gcc manually."
fi

echo "Compiling ajazz_daemon using make..."
make clean
make

echo "Installing static files using make install..."
make install

echo "Setting up dynamically generated udev rules..."
# Extract IDs from the C file

echo "Please click and move your mouse now to wake it up."
read -p "Press [Enter] once your mouse is awake..."

VENDOR_ID=$(awk '/#define VENDOR_ID/ {print $3}' ajazz_daemon.c | sed 's/0x//' | head -n 1)
PRODUCT_ID=$(awk '/#define PRODUCT_ID/ {print $3}' ajazz_daemon.c | sed 's/0x//' | head -n 1)

if [ -z "$VENDOR_ID" ]; then
    VENDOR_ID="249a"
fi
if [ -z "$PRODUCT_ID" ]; then
    PRODUCT_ID="5c2f"
fi

echo "Using Vendor ID: $VENDOR_ID, Product ID: $PRODUCT_ID"

echo "SUBSYSTEM==\"usb\", ATTR{idVendor}==\"$VENDOR_ID\", ATTR{idProduct}==\"$PRODUCT_ID\", MODE=\"0666\"" > /etc/udev/rules.d/99-ajazz.rules

echo "Executing state changes..."
udevadm control --reload-rules && udevadm trigger
systemctl daemon-reload
systemctl enable --now ajazz-mouse.service

echo "Installation complete!"
echo "The battery status will be written to /tmp/ajazz_battery."
