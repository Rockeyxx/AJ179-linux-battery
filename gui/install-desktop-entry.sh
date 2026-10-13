#!/bin/sh
# Adds the AJ179 app to your application menu, running it from this checkout.
# Remove it with: rm ~/.local/share/applications/aj179.desktop
set -e
gui=$(cd "$(dirname "$0")" && pwd)
uv=$(command -v uv) || { echo "uv not found - install it first" >&2; exit 1; }
dir=${XDG_DATA_HOME:-$HOME/.local/share}/applications
mkdir -p "$dir"
cat > "$dir/aj179.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=AJ179
GenericName=Mouse settings
Comment=Battery, DPI, lighting, buttons and macros for the Ajazz AJ179
Exec="$uv" run --project "$gui" "$gui/ajazz_gui.py"
Icon=$gui/icons/aj179.svg
Terminal=false
Categories=Settings;HardwareSettings;
Keywords=ajazz;mouse;battery;dpi;
StartupWMClass=aj179
EOF
echo "Added $dir/aj179.desktop - open AJ179 from the app launcher."
