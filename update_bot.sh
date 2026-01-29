#!/bin/bash

# Book Club Bot Update Script

echo "📚 Updating Book Club Bot..."
echo ""

# Stop the service
echo "⏸️  Stopping bookclub-bot service..."
sudo systemctl stop bookclub-bot

if [ $? -eq 0 ]; then
    echo "✅ Service stopped"
else
    echo "❌ Failed to stop service"
    exit 1
fi

echo ""

# Navigate to bot directory
cd ~/bookclub-bot

# Stash any local changes
echo "💾 Stashing local changes..."
git stash

# Pull latest changes
echo "⬇️  Pulling latest changes from repository..."
git pull

if [ $? -eq 0 ]; then
    echo "✅ Pull successful"
else
    echo "❌ Pull failed"
    sudo systemctl start bookclub-bot
    exit 1
fi

# Restore stashed changes
echo "📦 Restoring stashed changes..."
git stash pop

echo ""

# Restart the service
echo "▶️  Starting bookclub-bot service..."
sudo systemctl start bookclub-bot

if [ $? -eq 0 ]; then
    echo "✅ Service started"
else
    echo "❌ Failed to start service"
    exit 1
fi

echo ""
echo "✨ Update complete! Checking status..."
echo ""

# Show service status
sudo systemctl status bookclub-bot --no-pager -l