# AJ179-linux-battery
A lightweight, efficient C daemon to read the battery percentage of Ajazz wireless mice on Linux. It runs in the background and writes the battery status to a local file, making it perfect for custom status bars like Waybar, Polybar, or Eww.  Tested on: AJ179

# Why use this?
The official Ajazz driver is Windows-only. This Linux alternative:

* **Respects Sleep Mode**: Unlike simple scripts, this daemon detects when your mouse goes to sleep and intelligently pauses, preventing USB crashes.

* **Ultra-Low Resource Usage**: Uses 0.0% CPU. It utilizes an event-driven sleep loop and only talks to the mouse when it's actively moving.

* **JSON Output**: Directly formatted for Waybar.

# How to check your Mouse IDs
This daemon defaults to the **Ajazz AJ179** IDs (`VENDOR_ID = 249a`, `PRODUCT_ID = 5c2f`).

If you have a different Ajazz model, you should check your IDs so you can provide them during installation.

To check the ids you need first to have usbutils: 

Arch:
```Bash
sudo pacman -S usbutils
```

Debian:
```Bash
sudo apt install usbutils
```

1. Do not plug in your mouse (or dongle) and run:
```Bash
lsusb
```
2. plug in your mouse and run:
```Bash
lsusb
```
3. Look for the new device appeared and take the ID for me was:

Bus 001 Device 002: ID 249a:5c2f XCTECH Wireless-Receiver
The format is ID [VENDOR]:[PRODUCT].
Vendor ID = 249a
Product ID = 5c2f

3. The installer will ask you for these IDs. If you are installing manually or via AUR, simply edit `/etc/conf.d/ajazz-battery` after installation to set your IDs.

# Installation

You can install the daemon either via the Arch User Repository (AUR), automatically using the provided script, or manually.

## AUR Installation (Arch Linux)

If you are using Arch Linux, you can install the package directly from the AUR using your preferred helper:

```Bash
yay -S aj179-linux-battery-git
```
*(If your mouse is not the AJ179, simply edit `/etc/conf.d/ajazz-battery` after installation and restart the service `ajazz-mouse.service`).*

## Automatic Installation

1. Make the installation script executable:
```Bash
chmod +x install.sh
```

2. Run the installation script (requires root and the mouse to be awake):
```Bash
sudo ./install.sh
```
The script will automatically detect your package manager (pacman or apt), install dependencies, compile the code via `make`, set up permissions, and configure the systemd service. It will also interactively ask if you want to configure custom mouse IDs.

*(Note: If the daemon fails to read battery status immediately after installation, physically unplug and re-plug the mouse dongle to force the kernel to evaluate the new udev rules).*

## Uninstallation

If you wish to remove the daemon, you can use the provided uninstallation script:
```Bash
chmod +x uninstall.sh
sudo ./uninstall.sh
```
This will safely stop the service, remove the binary, and clean up the systemd and udev rules.

## Manual Installation

1. Install Dependencies
You need `libusb`, `gcc`, and `make` to compile the code.

Arch:
```Bash
sudo pacman -S libusb gcc make
```

Debian:
```Bash
sudo apt install libusb-1.0-0-dev gcc make
```

2. Compile & install the code:
```Bash
make
sudo make install
```

3. Setup Configuration
 
The `Makefile` will automatically install a universal `udev` rule for Ajazz devices. However, you should update the configuration file if your IDs are different from the AJ179:

```Bash
sudo nano /etc/conf.d/ajazz-battery
```

4. Enable the Daemon (Auto-start)
Start and enable the installed service:

```Bash
sudo systemctl enable --now ajazz-mouse.service
```

# Waybar Integration
The daemon automatically writes the battery status to /tmp/ajazz_battery. 

Add this module to your **~/.config/waybar/config**:

in your("modules-right": [ here ]) or ("modules-left": [ here ]) add "custom/ajazz", then add this below in the config:

```JSON
"custom/ajazz": {
    "exec": "cat /tmp/ajazz_battery",
    "return-type": "json",
    "interval": 2,
    "tooltip": true
}
```
------------------------------------
# final notes
the bytes.txt can be used for different things i just do it for the battery if you can do a whole app with it you are free to use as you like. and this bytes are when you first start the ajazz app in windows 
if this code didnt work for you mostly the byte codes not for your model I reverse engineered it using wire shark try searching on the topic if you want to. I cant explain it here
