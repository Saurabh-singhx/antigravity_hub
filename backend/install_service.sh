#!/bin/bash
# Sets up Antigravity Hub to start automatically in the background on computer boot
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

SERVICE_FILE="$SERVICE_DIR/antigravity-hub.service"

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Antigravity Hub Local Notification Relay
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/saurabh/coding/antigravity_hub/backend
ExecStart=/home/saurabh/coding/antigravity_hub/backend/.venv/bin/python app.py
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

# Start the service right now
systemctl --user restart antigravity-hub.service

# Enable lingering so service runs even before GUI login
loginctl enable-linger "$USER" 2>/dev/null

echo "=========================================================="
echo "✅ Antigravity Hub is now installed as a background service!"
echo "It will automatically start whenever your computer boots."
echo ""
echo "Useful commands:"
echo "  Check Status:  systemctl --user status antigravity-hub"
echo "  Restart:       systemctl --user restart antigravity-hub"
echo "  Stop:          systemctl --user stop antigravity-hub"
echo "  View live logs: journalctl --user -u antigravity-hub -f"
echo "=========================================================="
