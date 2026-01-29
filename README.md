# Book Club Discord Bot - Setup & Usage Guide

## Overview

This Discord bot creates private book club channels with discussion threads for each chapter. It automatically maintains a live discussion guide that updates in real-time as members comment, and provides a public directory to browse all active and past book clubs.

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
   - ✅ Manage Roles
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 3. Install on Ubuntu Server

**Install Python and dependencies:**
```bash
sudo apt update
sudo apt install python3 python3-pip git
pip3 install discord.py
```

**Clone or create bot directory:**
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

### Using systemd (Recommended)

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
- Private text channel in the same category where you ran the command
- Thread for each chapter (all members auto-added)
- Live discussion guide that updates automatically
- Entry in the book club directory

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

### `/set_directory`

Sets the current channel as the public book club directory.

**Usage:** Run once in the channel you want to use as the directory

```
/set_directory
```

**What It Does:**
- Designates this channel as the directory
- Creates a list of all active and past book clubs
- Updates automatically when book clubs are created or archived
- Only one directory per server

**Directory Format:**
```
# 📚 Active Book Clubs

📖 **Book Name 1** - #book-channel-1
📖 **Book Name 2** - #book-channel-2

# 📕 Past Book Clubs

📕 **Archived Book 1** - #archived-book-1
📕 **Archived Book 2** - #archived-book-2
```

---

### `/set_archive_category`

Sets which category archived book clubs should be moved to.

**Usage:** Run once to configure (you can use your existing "Old books" category)

```
/set_archive_category category:[Select your category]
```

**What It Does:**
- Tells the bot where to move archived book clubs
- Only needs to be set once per server
- Works with existing categories

---

### `/archive_bookclub`

Archives the current book club and moves it to the archive category.

**Usage:** Must be used inside a book club channel

```
/archive_bookclub
```

**What Happens:**
- Channel is moved to the archive category (e.g., "Old books")
- Book club is marked as archived
- Moves from "Active" to "Past" section in the directory
- All discussion history is preserved

**Note:** You must set an archive category with `/set_archive_category` before using this command.

---

## How the Discussion Guide Works

The discussion guide is automatically created and maintained by the bot.

**Features:**
- Updates in real-time when anyone comments in a chapter thread
- Updates when messages are edited
- Shows reply context (when someone replies to another comment)
- Organizes comments by chapter in chronological order
- Strips spoiler tags (`||text||`) so the guide is readable
- Automatically splits into multiple messages if content exceeds Discord's character limit
- Header "Discussion Guide: Book Name" is visible, content is wrapped in spoiler tags

**Format:**
```
# Discussion Guide: Book Name
[Click to reveal spoiler]

## Chapter 1
**Username**: Comment text
  **ReplyUser** (replying to Username): Reply text
**AnotherUser**: Another comment

## Chapter 2
**Username**: Comment text
```

**Location:** Posted at the bottom of the book club channel

---

## Initial Configuration

After installing the bot, run these commands once to set up your server:

1. **Create a directory channel** (or use an existing one)
   - Example: Create a channel called `#book-club-directory`

2. **Set the directory:**
   ```
   /set_directory
   ```

3. **Set archive category** (if you have one for old books):
   ```
   /set_archive_category category:[Your "Old books" category]
   ```

Now you're ready to create book clubs!

---

## Tips & Best Practices

**For Book Club Members:**
- Use spoiler tags `||like this||` when commenting to avoid notification spoilers
- The discussion guide shows all comments without spoilers for easy reading
- Use Discord's reply feature - it shows in the guide as indented replies

**For Book Club Management:**
- Book clubs are created in the same category as the channel where you run `/create_bookclub`
- You can manually move channels between categories without breaking any features
- Use `/archive_bookclub` when a book club is finished
- The directory automatically updates to reflect active vs. past book clubs

**For Bot Management:**
- Bot must be running 24/7 for live updates to work
- If bot goes offline, guides will update when it comes back online
- All data is saved to files (`bookclubs.json`, `directories.json`, `archives.json`)
- Book clubs created with older versions will work with new features after update

---

## Updating the Bot

If you're running the bot from a git repository, you can use this update script:

**Create update script:**
```bash
nano ~/update_bot.sh
```

**Paste this:**
```bash
#!/bin/bash

echo "📚 Updating Book Club Bot..."
echo ""

echo "⏸️  Stopping bookclub-bot service..."
sudo systemctl stop bookclub-bot

if [ $? -eq 0 ]; then
    echo "✅ Service stopped"
else
    echo "❌ Failed to stop service"
    exit 1
fi

echo ""
cd ~/bookclub-bot

echo "💾 Stashing local changes..."
git stash

echo "⬇️  Pulling latest changes from repository..."
git pull

if [ $? -eq 0 ]; then
    echo "✅ Pull successful"
else
    echo "❌ Pull failed"
    sudo systemctl start bookclub-bot
    exit 1
fi

echo "📦 Restoring stashed changes..."
git stash pop

echo ""
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
sudo systemctl status bookclub-bot --no-pager -l
```

**Make it executable:**
```bash
chmod +x ~/update_bot.sh
```

**To update:**
```bash
~/update_bot.sh
```

---

## Troubleshooting

**Bot doesn't respond to commands:**
- Check bot is running: `sudo systemctl status bookclub-bot`
- Check logs: `sudo journalctl -u bookclub-bot -f`
- Verify privileged intents are enabled in Discord Developer Portal

**Discussion guide not updating:**
- Ensure bot is running continuously
- Check that the book club was created after the bot started (or restart bot to load existing clubs)
- Verify Message Content Intent is enabled

**Archive command says "No archive category set":**
- Run `/set_archive_category` first to designate where archived books should go

**Directory not showing book clubs:**
- Run `/set_directory` in the channel you want to use as the directory
- Restart the bot to ensure it loads all existing book clubs

---

## Data Persistence

The bot stores data in three JSON files in the bot directory:

- `bookclubs.json` - All book club information
- `directories.json` - Directory channel configuration
- `archives.json` - Archive category settings

These files persist across bot restarts, so your book clubs are never lost.

**Backup recommendation:** Periodically backup these files to prevent data loss.

---

## Security Notes

- Keep your bot token secret - never share it or commit it to version control
- Only bot administrators should have access to the Ubuntu server
- The bot only has access to channels it creates or is explicitly invited to
- Book club channels are private - only mentioned members can access them
- Consider using `.gitignore` to exclude `bookclubs.json` and token if using version control