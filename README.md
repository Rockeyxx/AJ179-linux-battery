# AJ179-linux-battery
A small C daemon and command-line tool for the **Ajazz AJ179** wireless mouse on Linux. The daemon reads the battery level through the receiver's `hidraw` interface and writes it to a file for status bars like **Waybar**, **Polybar**, or **Eww**. The `ajazzctl` tool changes the mouse settings that the official Windows driver offers.

---

## Table of Contents
* [Features](#features)
* [Finding Mouse IDs](#how-to-check-your-mouse-ids)
* [Installation](#installation)
    * [AUR (Arch Linux)](#aur-installation-arch-linux)
    * [Automatic Installation](#automatic-installation)
    * [Manual Installation](#manual-installation)
* [Waybar Integration](#waybar-integration)
* [Mouse Settings (ajazzctl)](#mouse-settings-ajazzctl)
* [Technical Notes & Credits](#technical-notes--credits)

---

## Features
The official Ajazz driver is Windows-only. This Linux alternative:

* **Battery right away**: asks for the battery level when it starts, then listens for the updates the mouse sends on its own. It keeps showing the last level while the mouse sleeps.

* **Receiver or cable**: uses the USB cable when the mouse is plugged in (the level then shows ⚡ and the Waybar class `charging`) and the 2.4 GHz receiver otherwise. `ajazzctl` follows the same rule.

* **Leaves the USB device alone**: it uses the kernel's `hidraw` node and never detaches the kernel driver, so it causes no USB re-enumeration.

* **Mouse settings**: report rate, DPI stages and colours, lighting, lift-off distance, Motion Sync, Angle Snap, power options, button mapping and macros (see [ajazzctl](#mouse-settings-ajazzctl)).

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
2.  Execute with elevated privileges:
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
sudo pacman -S gcc make
```
Debian:
```Bash
sudo apt install gcc make
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

## Mouse Settings (ajazzctl)

`ajazzctl` is installed next to the daemon and runs as your normal user. Settings only reach the mouse while it is awake, so move it if the tool says it is asleep or idle; it waits and retries. Each change is read back from the mouse to confirm it.

```Bash
ajazzctl show                          # all current settings
ajazzctl info                          # device id, sensor, battery
ajazzctl rate 1000                     # 125, 250, 500 or 1000 Hz
ajazzctl dpi 2 1600                    # set DPI stage 2
ajazzctl dpi select 2                  # make stage 2 active
ajazzctl dpi-colour 2 '#00ff00'        # LED colour of stage 2
ajazzctl lighting constant '#ff00ff' 4 0   # off | breathing | constant [#RRGGBB] [brightness speed]
ajazzctl sensor lod 1                  # lift-off distance: 1 = 1 mm, 2 = 2 mm
ajazzctl sensor motion-sync on
ajazzctl sensor angle-snap off
ajazzctl power wake-on-move on
ajazzctl button 4 key:ctrl+c           # buttons: 1 left (locked) 2 right 3 middle 4 back 5 forward 6 dpi
ajazzctl macro 5 ctrl+c wait:50 ctrl+v
ajazzctl buttons reset                 # factory button mapping
```

Run `ajazzctl` without arguments for the full list. The mouse has no command to read button mappings back, so `ajazzctl` remembers the last mapping it wrote in `~/.config/ajazzctl/buttons`. Button 1 (left click) cannot be remapped, so a mistake can always be undone.

---

## Technical Notes & Credits

### Reverse Engineering
The protocol was decompiled from the official **AJAZZ Driver (X) 1.0.7.0** and checked against the mouse. [docs/PROTOCOL.md](docs/PROTOCOL.md) documents every command, the code address it came from, and which parts were confirmed on hardware. Firmware update commands are deliberately not implemented.

### Disclaimer
* **Experimental:** This utility is an independent implementation and is not affiliated with Ajazz.
* **Permissions:** The installer deploys a `udev` rule to `/etc/udev/rules.d/` that gives the logged-in user access to the receiver's `hidraw` nodes.

### Contributions
Other Ajazz models are not supported yet. If you have one, the output of `ajazzctl info` and `lsusb` in an **Issue** is a good start, and **Pull Requests** are welcome. Run `make test` before sending changes.

---

**Developer:** [Rockeyxx](https://github.com/Rockeyxx)
**Tested Hardware:** Ajazz AJ179
**License:** MIT
