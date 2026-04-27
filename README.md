# AJ179-linux-battery
A lightweight, high-efficiency C daemon designed to interface with **Ajazz wireless mice** on Linux. It retrieves battery telemetry via `libusb` and writes the state to a local buffer, facilitating integration with status bars like **Waybar**, **Polybar**, or **Eww**.

---

## Table of Contents
* [Features](#features)
* [Finding Mouse IDs](#how-to-check-your-mouse-ids)
* [Installation](#installation)
    * [AUR (Arch Linux)](#aur-installation-arch-linux)
    * [Automatic Installation](#automatic-installation)
    * [Manual Installation](#manual-installation)
* [Waybar Integration](#waybar-integration)
* [Technical Notes & Credits](#technical-notes--credits)

---

## Features
The official Ajazz driver is Windows-only. This Linux alternative:

* **Respects Sleep Mode**: Unlike simple scripts, this daemon detects when your mouse goes to sleep and intelligently pauses, preventing USB crashes.

* **Ultra Low Resource Usage**: Uses 0.0% CPU. It utilizes an event-driven sleep loop and only talks to the mouse when it's actively moving.

* **JSON Output**: Directly formatted for Waybar.

---

## How to Check Your Mouse IDs

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

Bus 001 Device 002: ID **249a:5c2f** XCTECH Wireless-Receiver

The format is ID [VENDOR]:[PRODUCT].
Vendor ID = 249a
Product ID = 5c2f

 The installer will ask you for these IDs. If you are installing manually or via AUR, simply edit `/etc/conf.d/ajazz-battery` after installation to set your IDs.
 
---

## Installation

### AUR Installation (Arch Linux)
you can use AUR. Or the auto installtion if preferred. 

```bash
yay -S aj179-linux-battery-git
```

### Automatic Installation
The included `install.sh` script automates dependency installation, compilation via `make`, and `systemd` service initialization. It will also interactively ask if you want to configure custom mouse IDs.

1.  Grant execution permissions:
    ```bash
    chmod +x install.sh
    ```
2.  Execute with elevated privileges (requires mouse movment):
    ```bash
    sudo ./install.sh
    ```
*Note: If the daemon fails to read battery state immediately after installation, physically unplug and replug the USB dongle to trigger the new `udev` rules.*

---
### Manual Installation
For users preferring manual deployment or packaging:

1.  **Install Dependencies:**

Arch:
```Bash
sudo pacman -S libusb gcc make
```
Debian:
```Bash
sudo apt install libusb-1.0-0-dev gcc make
```
2.  **Compile & Deploy:**
    ```bash
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

---

## Waybar Integration

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
---

## Technical Notes & Credits

### Reverse Engineering
The control bytes used in this daemon were identified via **USB traffic analysis (Wireshark)**. The implementation mimics the initial handshake and status request sent by the Windows driver to the ajaz 179 app.

### Disclaimer
* **Experimental:** This utility is an independent implementation and is not affiliated with Ajazz.
* **Bus Permissions:** The installer deploys a `udev` rule to `/etc/udev/rules.d/` to allow unprivileged access to the mouse's USB interface.

### Contributions
The `bytes.txt` file contains raw data captured during the Windows driver initialization. If you identify byte sequences for RGB control, DPI switching, or other Ajazz models, please open a **Pull Request** or an **Issue** to help expand the project.

---

**Developer:** [Rockeyxx](https://github.com/Rockeyxx)
**Tested Hardware:** Ajazz AJ179
**License:** MIT
