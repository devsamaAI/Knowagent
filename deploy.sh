#!/bin/bash
# =============================================================================
# KnowAgent — Deployment Script
# Works on: Raspberry Pi OS, Ubuntu, Debian
#
# Run this ONCE on a fresh device:
#   chmod +x deploy.sh && ./deploy.sh
# =============================================================================

set -e  # Exit immediately if any command fails

REPO_URL="https://github.com/devsamaAI/Knowagent.git"
APP_DIR="$HOME/pocket-agent"
SERVICE_NAME="pocket-agent"

echo "========================================"
echo "  KnowAgent — Deployment"
echo "========================================"

# 1. System packages (libpq-dev needed for psycopg2 on ARM/Pi)
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git libpq-dev gcc

# 2. Clone or update repo
echo "[2/6] Cloning repository..."
if [ -d "$APP_DIR" ]; then
    echo "  Directory exists — pulling latest changes..."
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

# 3. Python virtual environment + dependencies
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
    echo "  ⚠️  .env file created — fill in your secrets now:"
    echo "  nano $APP_DIR/.env"
    echo ""
    echo "  Required:"
    echo "    TELEGRAM_BOT_TOKEN=..."
    echo "    GROQ_API_KEY=..."
    echo "    DATABASE_URL=postgresql://...  (from neon.tech)"
    echo ""
    read -p "  Press Enter after filling in .env to continue..."
else
    echo "  .env already exists — skipping."
fi

# 5. systemd user service
echo "[5/6] Setting up systemd service..."
mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/$SERVICE_NAME.service" << EOF
[Unit]
Description=KnowAgent Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"

# 6. Enable lingering (keeps service alive after SSH logout)
echo "[6/6] Enabling lingering (survives SSH logout)..."
sudo loginctl enable-linger "$USER"

echo ""
echo "========================================"
echo "  ✅ Deployment complete!"
echo "========================================"
echo ""
echo "Bot status:    systemctl --user status $SERVICE_NAME"
echo "Live logs:     journalctl --user -u $SERVICE_NAME -f"
echo "Restart:       systemctl --user restart $SERVICE_NAME"
echo "Stop:          systemctl --user stop $SERVICE_NAME"
echo ""
echo "After code updates:"
echo "  git -C $APP_DIR pull && systemctl --user restart $SERVICE_NAME"
echo ""
