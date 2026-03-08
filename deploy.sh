#!/bin/bash
# =============================================================================
# Pocket Agent — Oracle Cloud VM Deployment Script
# Run this ONCE on a fresh Ubuntu VM:
#   chmod +x deploy.sh && ./deploy.sh
# =============================================================================

set -e  # Exit immediately if any command fails

REPO_URL="YOUR_GITHUB_REPO_URL_HERE"   # e.g. https://github.com/yourname/pocket-agent
APP_DIR="$HOME/pocket-agent"
SERVICE_NAME="pocket-agent"

echo "=== Pocket Agent Deployment ==="

# 1. System packages
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git

# 2. Clone repo
echo "[2/6] Cloning repository..."
if [ -d "$APP_DIR" ]; then
    echo "  Directory exists — pulling latest changes..."
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

# 3. Python virtual environment
echo "[3/6] Setting up Python environment..."
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# 4. .env file
echo "[4/6] Setting up environment variables..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo ""
    echo "  ⚠️  .env file created from template."
    echo "  You MUST fill in your secrets before starting the bot:"
    echo "  nano $APP_DIR/.env"
    echo ""
else
    echo "  .env already exists — skipping."
fi

# 5. systemd user service
echo "[5/6] Setting up systemd service..."
mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/$SERVICE_NAME.service" << EOF
[Unit]
Description=Pocket Agent Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"

# 6. Enable lingering (so service survives SSH logout)
echo "[6/6] Enabling user lingering..."
sudo loginctl enable-linger "$USER"

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Fill in your secrets:   nano $APP_DIR/.env"
echo "  2. Start the bot:          systemctl --user start $SERVICE_NAME"
echo "  3. Check it's running:     systemctl --user status $SERVICE_NAME"
echo "  4. View live logs:         journalctl --user -u $SERVICE_NAME -f"
echo ""
echo "After code updates:"
echo "  git -C $APP_DIR pull && systemctl --user restart $SERVICE_NAME"
