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
if [ -n "$SUDO_USER" ]; then
    sudo -u "$SUDO_USER" make clean
    sudo -u "$SUDO_USER" make
else
    make clean
    make
fi

echo "Installing static files using make install..."
make install

echo "Please click and move your mouse now to wake it up."
read -p "Press [Enter] once your mouse is awake..."

read -p "Do you want to configure custom mouse IDs? (Default is Ajazz AJ179: 249a/5c2f) [y/N]: " config_choice
if [[ "$config_choice" =~ ^[Yy]$ ]]; then
    read -p "Enter Vendor ID (e.g. 249a): " VENDOR_ID
    read -p "Enter Product ID (e.g. 5c2f): " PRODUCT_ID
    echo "VENDOR_ID=$VENDOR_ID" > /etc/conf.d/ajazz-battery
    echo "PRODUCT_ID=$PRODUCT_ID" >> /etc/conf.d/ajazz-battery
    echo "Configuration saved to /etc/conf.d/ajazz-battery."
fi

echo "Executing state changes..."
udevadm control --reload-rules && udevadm trigger
systemctl daemon-reload
systemctl enable --now ajazz-mouse.service

echo "Installation complete!"
echo "The battery status will be written to /tmp/ajazz_battery."
