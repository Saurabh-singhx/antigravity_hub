#!/bin/bash
# Installs Antigravity Hub to start automatically in the background on computer boot
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_BIN="$DIR/.venv/bin/python"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "Creating virtual environment..."
    /usr/bin/python3.12 -m venv "$DIR/.venv"
    "$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt"
fi

# Ensure python binary in venv points to 3.12
ln -sf /usr/bin/python3.12 "$DIR/.venv/bin/python" 2>/dev/null || true
ln -sf /usr/bin/python3.12 "$DIR/.venv/bin/python3" 2>/dev/null || true

SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

SERVICE_FILE="$SERVICE_DIR/antigravity-hub.service"

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Antigravity Hub Local Notification & Interview Prep Relay
After=network.target

[Service]
Type=simple
WorkingDirectory=$DIR
ExecStart=$PYTHON_BIN app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=HUB_PORT=8765
Environment=HUB_HOST=0.0.0.0

[Install]
WantedBy=default.target
EOF

echo "✓ Created systemd user service at $SERVICE_FILE"

# Reload systemd user daemon
systemctl --user daemon-reload

# Enable service to run automatically on system boot
systemctl --user enable antigravity-hub.service

# Start / restart the service right now
systemctl --user restart antigravity-hub.service

# Enable lingering so user services start automatically on boot without waiting for GUI login
loginctl enable-linger "$USER" 2>/dev/null || true

# Clean up any legacy XDG desktop autostart entry to prevent port collision with systemd
rm -f "$HOME/.config/autostart/antigravity-hub.desktop"
echo "✓ Verified no conflicting XDG desktop autostart entries"
echo "=========================================================="
echo "✅ Antigravity Hub is configured to auto-start on PC boot!"
echo ""
echo "Current Service Status:"
systemctl --user status antigravity-hub.service --no-pager
echo "=========================================================="
