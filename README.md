# AJ179-linux-battery
A lightweight, efficient C daemon to read the battery percentage of Ajazz wireless mice on Linux. It runs in the background and writes the battery status to a local file, making it perfect for custom status bars like Waybar, Polybar, or Eww.  Tested on: AJ179

# Why use this?
The official Ajazz driver is Windows-only. This Linux alternative:

* **Respects Sleep Mode**: Unlike simple scripts, this daemon detects when your mouse goes to sleep and intelligently pauses, preventing USB crashes.

* **Ultra-Low Resource Usage**: Uses 0.0% CPU. It utilizes an event-driven sleep loop and only talks to the mouse when it's actively moving.

* **JSON Output**: Directly formatted for Waybar.

# How to check your Mouse IDs (Important)
This code is configured for VENDOR_ID = **0x249a** and PRODUCT_ID = **0x5c2f**. 

If you have a different Ajazz model, you need to check your IDs and update the code.

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

3. Update the C code: If your IDs are different, open ajazz_daemon.c and edit these lines at the top:
```C
#define VENDOR_ID  0x249a // Change to your Vendor ID
#define PRODUCT_ID 0x5c2f // Change to your Product ID
```
(Note: Keep the 0x in front of the numbers it is hexadecimal).

# Installation:
1. Install Dependencies
You need libusb and gcc to compile the code.

Arch:
```Bash
sudo pacman -S libusb gcc
```

Debian:
```Bash
sudo apt install libusb-1.0-0-dev gcc
```

2. Compile & install the code ajazz_daemon.c:
```Bash
gcc ajazz_daemon.c -o ajazz_daemon -lusb-1.0
sudo mv ajazz_daemon /usr/local/bin/
```

3. Setup Permissions (udev rule)
 
Create a rule so the daemon can access the USB device without needing sudo. (Change 249a and 5c2f below, if your ids are different).

```Bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="249a", ATTR{idProduct}=="5c2f", MODE="0666"' | sudo tee /etc/udev/rules.d/99-ajazz.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```
4. Enable the Daemon (Auto-start)
Create a systemd service file (nano or any editor):

```Bash
sudo nano /etc/systemd/system/ajazz-mouse.service
```
Paste the following configuration:
```Ini, TOML
[Unit]
Description=Ajazz Mouse Battery Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ajazz_daemon
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Start and enable the service:

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
