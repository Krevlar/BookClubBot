# Book Club Discord Bot - Setup & Usage Guide

## Overview

This Discord bot creates private book club channels with discussion threads for each chapter. It automatically maintains a live discussion guide that updates in real-time as members comment.

---

## Initial Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name (e.g., "Book Club Bot")
3. Go to the **"Bot"** section in the left sidebar
4. Click **"Add Bot"** and confirm
5. Under **"Privileged Gateway Intents"**, enable:
   - ✅ Message Content Intent
   - ✅ Server Members Intent
6. Click **"Reset Token"** and copy your bot token (save this securely!)

### 2. Invite Bot to Your Server

1. In the Discord Developer Portal, go to **"OAuth2"** → **"URL Generator"**
2. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select bot permissions:
   - ✅ Manage Channels
   - ✅ Manage Threads
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Send Messages in Threads
   - ✅ Manage Messages
   - ✅ Read Message History
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 3. Install on Ubuntu Server

**Install Python and dependencies:**
```bash
sudo apt update
sudo apt install python3 python3-pip
pip3 install discord.py
```

**Create bot directory:**
```bash
mkdir ~/bookclub-bot
cd ~/bookclub-bot
```

**Create the bot file:**
```bash
nano bot.py
```

Paste the bot code from the artifact, then save (Ctrl+X, Y, Enter).

**Add your bot token:**

Edit the last line of `bot.py` and replace `YOUR_BOT_TOKEN` with your actual token:
```python
bot.run('YOUR_ACTUAL_TOKEN_HERE')
```

**Test the bot:**
```bash
python3 bot.py
```

You should see: `Bot is now running!` and `Synced X command(s)`

Press Ctrl+C to stop.

---

## Running the Bot 24/7

### Option A: Using systemd (Recommended)

This makes the bot start automatically on boot and restart if it crashes.

**1. Create a service file:**
```bash
sudo nano /etc/systemd/system/bookclub-bot.service
```

**2. Paste this configuration** (replace `YOUR_USERNAME` with your actual Ubuntu username):
```ini
[Unit]
Description=Book Club Discord Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/bookclub-bot
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/bookclub-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save with Ctrl+X, Y, Enter.

**3. Enable and start the service:**
```bash
sudo systemctl enable bookclub-bot
sudo systemctl start bookclub-bot
```

**4. Useful commands:**

Check if bot is running:
```bash
sudo systemctl status bookclub-bot
```

View logs:
```bash
sudo journalctl -u bookclub-bot -f
```

Restart bot:
```bash
sudo systemctl restart bookclub-bot
```

Stop bot:
```bash
sudo systemctl stop bookclub-bot
```

### Option B: Using screen (Manual)

Simple but requires you to manually restart after reboots.

**Start the bot in a detached screen:**
```bash
screen -S bookclub
cd ~/bookclub-bot
python3 bot.py
```

**Detach from screen:** Press `Ctrl+A`, then `D`

**Reattach to screen:**
```bash
screen -r bookclub
```

**Stop the bot:** Reattach and press `Ctrl+C`

---

## Bot Commands

### `/create_bookclub`

Creates a new book club with private channel, chapter threads, and live discussion guide.

**Usage:** Type `/create_bookclub` in any Discord channel

**Interactive Setup:**

1. **Book Name** - Enter the book title
   - Example: `Pride and Prejudice`

2. **Chapters** - Enter chapters in format: `Name, 1-5, Name`
   - Examples:
     - `Prologue, 1-10, Epilogue`
     - `1-15`
     - `Introduction, 1-3, Interlude, 4-6, Conclusion`
     - `The Beginning, The Middle, The End`

3. **Members** - Mention users with @ (space-separated)
   - Example: `@Alice @Bob @Charlie`

**What Gets Created:**
- Private text channel (only specified members can see it)
- Thread for each chapter (all members auto-added)
- Live discussion guide that updates automatically

---

### `/add_member`

Adds a new member to the current book club.

**Usage:** Must be used inside a book club channel

```
/add_member member:@NewPerson
```

**What Happens:**
- Member gains access to the channel
- Member is added to all chapter threads
- Discussion guide remains accessible to them

---

## How the Discussion Guide Works

The discussion guide is automatically created and maintained by the bot.

**Features:**
- Updates in real-time when anyone comments in a chapter thread
- Organizes comments by chapter in chronological order
- Strips spoiler tags (`||text||`) so the guide is readable
- Automatically splits into multiple messages if content exceeds Discord's character limit

**Format:**
```
# Discussion Guide: Book Name

## Chapter 1
**Username**: Comment text
**AnotherUser**: Another comment

## Chapter 2
**Username**: Comment text
```

**Location:** Posted at the bottom of the book club channel

---

## Tips & Best Practices

**For Book Club Members:**
- Use spoiler tags `||like this||` when commenting to avoid notification spoilers
- The discussion guide shows all comments without spoilers for easy reading

**For Bot Management:**
- Bot must be running 24/7 for live updates to work
- If bot goes offline, the guide will update when it comes back online
- Each book club is independent with its own channel and threads
- You can create multiple book clubs on the same server

**Troubleshooting:**
- If commands don't appear, wait a few minutes for Discord to sync them
- If bot stops working, check logs: `sudo journalctl -u bookclub-bot -f`
- To update the bot code, edit `bot.py` and restart: `sudo systemctl restart bookclub-bot`

---

## Security Notes

- Keep your bot token secret - never share it or commit it to version control
- Only bot administrators should have access to the Ubuntu server
- The bot only has access to channels it creates or is explicitly invited to
- Book club channels are private - only mentioned members can access them