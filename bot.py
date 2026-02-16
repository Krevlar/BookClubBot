async def update_discussion_guide(book_club, guild):
    """Update the live discussion guide, splitting into multiple messages if needed"""
    if not book_club.guide_message_ids:
        return
    
    try:
        channel = await guild.fetch_channel(book_club.channel_id)
        
        # Generate the header (not spoilered)
        header = f"# Discussion Guide: {book_club.book_name}\n"
        
        # Generate the guide content (will be spoilered per chunk)
        guide_content = await generate_guide_content(book_club, guild)
        
        # Split content into chunks (~1900 chars to leave room for spoiler tags)
        chunks = split_into_chunks(guide_content, 1900)
        
        # First message includes the header + first chunk
        if chunks:
            chunks[0] = header + chunks[0]
        else:
            chunks = [f"{header}||*No comments yet. The guide will update automatically as people comment!*||"]
        
        # Update existing messages or create new ones
        for i, chunk in enumerate(chunks):
            if i < len(book_club.guide_message_ids):
                # Update existing message
                try:
                    msg = await channel.fetch_message(book_club.guide_message_ids[i])
                    await msg.edit(content=chunk)
                except:
                    # If message was deleted, create a new one
                    new_msg = await channel.send(chunk)
                    book_club.guide_message_ids[i] = new_msg.id
            else:
                # Create new message for additional chunks
                new_msg = await channel.send(chunk)
                book_club.guide_message_ids.append(new_msg.id)
        
        # Delete extra messages if content got shorter
        if len(chunks) < len(book_club.guide_message_ids):
            for i in range(len(chunks), len(book_club.guide_message_ids)):
                try:
                    msg = await channel.fetch_message(book_club.guide_message_ids[i])
                    await msg.delete()
                except:
                    pass
            book_club.guide_message_ids = book_club.guide_message_ids[:len(chunks)]
        
        save_book_clubs()
    
    except Exception as e:
        print(f"Error updating discussion guide: {e}")
import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
from datetime import datetime, timedelta

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Store book club data
book_clubs = {}
directory_channels = {}  # {guild_id: {'channel_id': id, 'message_ids': [id1, id2, id3]}}
archive_categories = {}  # {guild_id: category_id}
manual_book_clubs = {}  # {guild_id: [{'name': str, 'channel_id': int, 'archived': bool}]}
DATA_FILE = 'bookclubs.json'
DIRECTORY_FILE = 'directories.json'
ARCHIVE_FILE = 'archives.json'
MANUAL_FILE = 'manual_bookclubs.json'

def save_book_clubs():
    """Save book clubs to file"""
    data = {}
    for book_club_id, book_club in book_clubs.items():
        data[book_club_id] = {
            'guild_id': book_club.guild_id,
            'book_name': book_club.book_name,
            'channel_id': book_club.channel_id,
            'thread_ids': book_club.thread_ids,
            'members': book_club.members,
            'chapters': book_club.chapters,
            'guide_message_ids': book_club.guide_message_ids,
            'is_archived': book_club.is_archived,
            'creator_id': book_club.creator_id,
            'inactive_members': book_club.inactive_members
        }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def save_directories():
    """Save directory channels to file"""
    with open(DIRECTORY_FILE, 'w') as f:
        json.dump(directory_channels, f, indent=2)

def save_archive_categories():
    """Save archive categories to file"""
    with open(ARCHIVE_FILE, 'w') as f:
        json.dump(archive_categories, f, indent=2)

def save_manual_book_clubs():
    """Save manual book clubs to file"""
    with open(MANUAL_FILE, 'w') as f:
        json.dump(manual_book_clubs, f, indent=2)

def load_book_clubs():
    """Load book clubs from file"""
    global book_clubs
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            for book_club_id, bc_data in data.items():
                book_clubs[book_club_id] = BookClub(
                    bc_data['guild_id'],
                    bc_data['book_name'],
                    bc_data['channel_id'],
                    bc_data['thread_ids'],
                    bc_data['members'],
                    bc_data['chapters'],
                    bc_data['guide_message_ids'],
                    bc_data.get('is_archived', False),
                    bc_data.get('creator_id'),
                    bc_data.get('inactive_members', [])
                )

def load_directories():
    """Load directory channels from file"""
    global directory_channels
    if os.path.exists(DIRECTORY_FILE):
        with open(DIRECTORY_FILE, 'r') as f:
            directory_channels = json.load(f)
            # Convert string keys to integers
            directory_channels = {int(k): v for k, v in directory_channels.items()}

def load_archive_categories():
    """Load archive categories from file"""
    global archive_categories
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r') as f:
            archive_categories = json.load(f)
            # Convert string keys to integers
            archive_categories = {int(k): int(v) for k, v in archive_categories.items()}

def load_manual_book_clubs():
    """Load manual book clubs from file"""
    global manual_book_clubs
    if os.path.exists(MANUAL_FILE):
        with open(MANUAL_FILE, 'r') as f:
            manual_book_clubs = json.load(f)
            # Convert string keys to integers
            manual_book_clubs = {int(k): v for k, v in manual_book_clubs.items()}
            
            # Migration: add 'archived' field to any entries missing it
            migrated = False
            for guild_id, clubs in manual_book_clubs.items():
                for club in clubs:
                    if 'archived' not in club:
                        club['archived'] = False
                        migrated = True
            
            if migrated:
                save_manual_book_clubs()
                print("Migrated legacy book clubs to include archived field")

def parse_chapters(chapter_string):
    """Parse chapter string like 'Prologue, 1-5, Epilogue' into a list of chapter names"""
    chapters = []
    parts = [p.strip() for p in chapter_string.split(',')]
    
    for part in parts:
        # Check if it's a range (e.g., "1-5")
        if '-' in part and all(x.strip().isdigit() for x in part.split('-')):
            range_parts = part.split('-')
            start = int(range_parts[0].strip())
            end = int(range_parts[1].strip())
            for i in range(start, end + 1):
                chapters.append(f"Chapter {i}")
        # Check if it's just a number
        elif part.isdigit():
            chapters.append(f"Chapter {part}")
        # Otherwise it's a named chapter
        else:
            chapters.append(part)
    
    return chapters

class BookClub:
    def __init__(self, guild_id, book_name, channel_id, thread_ids, members, chapters, guide_message_ids=None, is_archived=False, creator_id=None, inactive_members=None):
        self.guild_id = guild_id
        self.book_name = book_name
        self.channel_id = channel_id
        self.thread_ids = thread_ids
        self.members = members
        self.chapters = chapters
        self.guide_message_ids = guide_message_ids or []
        self.is_archived = is_archived
        self.creator_id = creator_id  # Track who created the book club
        self.inactive_members = inactive_members or []  # Members who stopped reading

@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')
    load_book_clubs()
    load_directories()
    load_archive_categories()
    load_manual_book_clubs()
    
    # Load active categories
    bot.active_categories = {}
    active_file = 'active_categories.json'
    if os.path.exists(active_file):
        with open(active_file, 'r') as f:
            data = json.load(f)
            bot.active_categories = {int(k): int(v) for k, v in data.items()}
    
    print(f'Loaded {len(book_clubs)} book club(s)')
    print(f'Loaded {len(directory_channels)} directory channel(s)')
    print(f'Loaded {len(archive_categories)} archive category(ies)')
    print(f'Loaded {len(bot.active_categories)} active category(ies)')
    print(f'Loaded {len(manual_book_clubs)} guild(s) with manual book clubs')
    
    # Start the inactivity check task
    check_inactive_readers.start()
    
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error syncing commands: {e}')

@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Check if message is in a thread that belongs to a book club
    if isinstance(message.channel, discord.Thread):
        # Find which book club this thread belongs to
        for book_club_id, book_club in book_clubs.items():
            if message.channel.id in book_club.thread_ids.values():
                # Update the discussion guide
                await update_discussion_guide(book_club, message.guild)
                # Update the directory (for reader progress)
                await update_book_club_list(message.guild)
                break
    
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    # Ignore bot messages
    if after.author.bot:
        return
    
    # Check if edited message is in a thread that belongs to a book club
    if isinstance(after.channel, discord.Thread):
        # Find which book club this thread belongs to
        for book_club_id, book_club in book_clubs.items():
            if after.channel.id in book_club.thread_ids.values():
                # Update the discussion guide
                await update_discussion_guide(book_club, after.guild)
                # Update the directory (for reader progress)
                await update_book_club_list(after.guild)
                break

async def generate_guide_content(book_club, guild):
    """Generate the discussion guide content"""
    guide_parts = []
    
    for chapter in book_club.chapters:
        thread_id = book_club.thread_ids.get(chapter)
        if not thread_id:
            continue
        
        try:
            thread = await guild.fetch_channel(thread_id)
            messages = []
            
            async for msg in thread.history(limit=None, oldest_first=True):
                if msg.author.bot or msg.type != discord.MessageType.default:
                    continue
                
                # Remove spoiler tags from content
                clean_content = msg.content.replace('||', '')
                
                # Check if this is a reply to another message
                if msg.reference and msg.reference.message_id:
                    try:
                        replied_msg = await thread.fetch_message(msg.reference.message_id)
                        replied_author = replied_msg.author.display_name
                        messages.append(f"  **{msg.author.display_name}** (replying to {replied_author}): {clean_content}")
                    except:
                        # If we can't fetch the replied message, just show it as a regular message
                        messages.append(f"**{msg.author.display_name}**: {clean_content}")
                else:
                    messages.append(f"**{msg.author.display_name}**: {clean_content}")
            
            if messages:
                guide_parts.append(f"\n## {chapter}\n" + "\n".join(messages))
        
        except Exception as e:
            guide_parts.append(f"\n## {chapter}\n*Error retrieving messages*")
    
    # Return content WITHOUT spoiler tags - they'll be added when splitting
    return "\n".join(guide_parts)

async def get_reader_progress(book_club, guild):
    """Get a summary of which members are reading and their latest chapter"""
    reader_progress = {}
    
    # Filter out inactive members
    active_member_ids = [m for m in book_club.members if m not in book_club.inactive_members]
    
    for member_id in active_member_ids:
        try:
            member = await guild.fetch_member(member_id)
            latest_chapter = None
            latest_chapter_index = -1
            latest_time = None
            
            # Check all threads for this member's most recent comment
            for i, (chapter, thread_id) in enumerate(book_club.thread_ids.items()):
                try:
                    thread = await guild.fetch_channel(thread_id)
                    async for msg in thread.history(limit=100):
                        if msg.author.id == member_id and msg.type == discord.MessageType.default:
                            if latest_time is None or msg.created_at > latest_time:
                                latest_time = msg.created_at
                                latest_chapter = chapter
                                latest_chapter_index = i
                            break  # Only check most recent message per thread
                except:
                    continue
            
            if latest_chapter:
                # Calculate progress percentage
                total_chapters = len(book_club.chapters)
                progress_percent = int(((latest_chapter_index + 1) / total_chapters) * 100)
                reader_progress[member.display_name] = {
                    'chapter': latest_chapter,
                    'progress': progress_percent
                }
        except:
            continue
    
    return reader_progress

@tasks.loop(hours=24)  # Run once per day
async def check_inactive_readers():
    """Check for inactive readers and message them"""
    print("Running inactivity check...")
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    
    for book_club_id, book_club in book_clubs.items():
        # Skip archived book clubs
        if book_club.is_archived:
            continue
        
        try:
            guild = bot.get_guild(book_club.guild_id)
            if not guild:
                continue
            
            for member_id in book_club.members:
                # Skip if already marked inactive
                if member_id in book_club.inactive_members:
                    continue
                
                try:
                    member = await guild.fetch_member(member_id)
                    latest_time = None
                    latest_chapter_index = -1
                    total_chapters = len(book_club.chapters)
                    
                    # Find their most recent comment
                    for i, thread_id in enumerate(book_club.thread_ids.values()):
                        try:
                            thread = await guild.fetch_channel(thread_id)
                            async for msg in thread.history(limit=100):
                                if msg.author.id == member_id and msg.type == discord.MessageType.default:
                                    if latest_time is None or msg.created_at > latest_time:
                                        latest_time = msg.created_at
                                        latest_chapter_index = i
                                    break
                        except:
                            continue
                    
                    # Check if they should be messaged
                    if latest_time and latest_time < two_weeks_ago:
                        # Don't message if they're on the last chapter (they likely finished)
                        if latest_chapter_index >= total_chapters - 1:
                            continue
                        
                        # Send DM asking if still reading
                        try:
                            dm_msg = await member.send(
                                f"Hi! I noticed you haven't commented on **{book_club.book_name}** in over 2 weeks. "
                                f"Are you still reading it? Reply with 'yes' or 'no'."
                            )
                            
                            # Wait for response (24 hours)
                            def check(m):
                                return m.author.id == member_id and m.channel == dm_msg.channel
                            
                            try:
                                response = await bot.wait_for('message', check=check, timeout=86400)  # 24 hours
                                if response.content.lower() in ['no', 'n', 'nope', 'not anymore', 'stopped']:
                                    # Mark as inactive
                                    book_club.inactive_members.append(member_id)
                                    save_book_clubs()
                                    await member.send(f"Got it! I've removed you from the active readers list for **{book_club.book_name}**.")
                            except asyncio.TimeoutError:
                                # No response - assume still reading
                                pass
                        except discord.Forbidden:
                            # Can't DM this user
                            pass
                
                except:
                    continue
            
            # Check if everyone has finished or stopped
            active_readers = [m for m in book_club.members if m not in book_club.inactive_members]
            if not active_readers and book_club.creator_id:
                try:
                    creator = await guild.fetch_member(book_club.creator_id)
                    channel = await guild.fetch_channel(book_club.channel_id)
                    await creator.send(
                        f"Hey! It looks like everyone has either finished or stopped reading **{book_club.book_name}**. "
                        f"You might want to archive it using `/archive_bookclub` in {channel.mention}."
                    )
                except:
                    pass
        
        except Exception as e:
            print(f"Error checking book club {book_club_id}: {e}")
    
    # Update all directories after inactivity check
    for guild_id in directory_channels.keys():
        try:
            guild = bot.get_guild(guild_id)
            if guild:
                await update_book_club_list(guild)
        except:
            pass

@check_inactive_readers.before_loop
async def before_inactivity_check():
    """Wait until bot is ready before starting the task"""
    await bot.wait_until_ready()

async def update_book_club_list(guild):
    """Update the public book club directory for a guild"""
    # Check if a directory channel exists for this guild
    if guild.id not in directory_channels:
        return
    
    directory_info = directory_channels[guild.id]
    
    try:
        directory_channel = await guild.fetch_channel(directory_info['channel_id'])
    except:
        # Directory channel was deleted
        del directory_channels[guild.id]
        save_directories()
        return
    
    # Get all book clubs for this guild
    all_book_clubs = [bc for bc in book_clubs.values() if bc.guild_id == guild.id]
    active_clubs = [bc for bc in all_book_clubs if not bc.is_archived]
    archived_clubs = [bc for bc in all_book_clubs if bc.is_archived]
    
    # Check if we need to recreate messages (new book club added, structure changed, etc.)
    needs_recreate = False
    if 'message_ids' not in directory_info or not directory_info['message_ids']:
        needs_recreate = True
    
    # If recreating, delete old messages
    if needs_recreate and 'message_ids' in directory_info:
        for msg_id in directory_info['message_ids']:
            try:
                old_msg = await directory_channel.fetch_message(msg_id)
                await old_msg.delete()
            except:
                pass
    elif needs_recreate and 'message_id' in directory_info:  # Handle old format
        try:
            old_msg = await directory_channel.fetch_message(directory_info['message_id'])
            await old_msg.delete()
        except:
            pass
    
    # Generate content
    message_ids = directory_info.get('message_ids', []) if not needs_recreate else []
    
    try:
        # Message 1: Active Book Clubs
        active_content = "# 📚 Active Book Clubs\n"
        active_content += "*Use `/join_bookclub` to join an active book, or `/unarchive_bookclub` to revive a past one.*\n\n"
        if active_clubs:
            for book_club in sorted(active_clubs, key=lambda x: x.book_name):
                try:
                    channel = await guild.fetch_channel(book_club.channel_id)
                    active_content += f"📖 **{book_club.book_name}** - <#{channel.id}>\n"
                    
                    # Get reader progress
                    progress = await get_reader_progress(book_club, guild)
                    if progress:
                        readers_list = []
                        for reader, info in sorted(progress.items()):
                            readers_list.append(f"{reader} ({info['chapter']}, {info['progress']}%)")
                        active_content += f"   *Readers: {', '.join(readers_list)}*\n"
                    
                    active_content += "\n"
                except:
                    active_content += f"📖 **{book_club.book_name}** - *(channel not found)*\n\n"
        
        # Active legacy books
        active_legacy = [bc for bc in manual_book_clubs.get(guild.id, []) if not bc.get('archived', True)]
        for manual_club in sorted(active_legacy, key=lambda x: x['name']):
            try:
                channel = await guild.fetch_channel(manual_club['channel_id'])
                active_content += f"📘 **{manual_club['name']}** - <#{channel.id}>\n\n"
            except:
                active_content += f"📘 **{manual_club['name']}** - *(channel not found)*\n\n"
        
        if not active_clubs and not active_legacy:
            active_content += "*No active book clubs. Use `/create_bookclub` to start one!*"
        
        if needs_recreate or len(message_ids) == 0:
            msg1 = await directory_channel.send(active_content)
            if len(message_ids) == 0:
                message_ids.append(msg1.id)
            else:
                message_ids[0] = msg1.id
        else:
            # Edit existing message
            try:
                msg1 = await directory_channel.fetch_message(message_ids[0])
                await msg1.edit(content=active_content)
            except:
                # Message was deleted, recreate
                msg1 = await directory_channel.send(active_content)
                message_ids[0] = msg1.id
        
        # Message 2: Past Book Clubs (if any)
        if archived_clubs:
            past_content = "# 📕 Past Book Clubs\n\n"
            for book_club in sorted(archived_clubs, key=lambda x: x.book_name):
                try:
                    channel = await guild.fetch_channel(book_club.channel_id)
                    past_content += f"📕 **{book_club.book_name}** - <#{channel.id}>\n"
                except:
                    past_content += f"📕 **{book_club.book_name}** - *(channel not found)*\n"
            
            if needs_recreate or len(message_ids) <= 1:
                msg2 = await directory_channel.send(past_content)
                if len(message_ids) <= 1:
                    message_ids.append(msg2.id)
                else:
                    message_ids[1] = msg2.id
            else:
                # Edit existing message
                try:
                    msg2 = await directory_channel.fetch_message(message_ids[1])
                    await msg2.edit(content=past_content)
                except:
                    # Message was deleted, recreate
                    msg2 = await directory_channel.send(past_content)
                    message_ids[1] = msg2.id
        
        # Message 3+: Legacy Book Clubs (if any) - split into multiple messages if needed
        legacy_start_index = 2 if archived_clubs else 1
        
        if guild.id in manual_book_clubs and manual_book_clubs[guild.id]:
            legacy_clubs = sorted(manual_book_clubs[guild.id], key=lambda x: x['name'])
            
            # Split into chunks of 20 book clubs per message
            chunk_size = 20
            legacy_msg_index = legacy_start_index
            
            for i in range(0, len(legacy_clubs), chunk_size):
                chunk = legacy_clubs[i:i + chunk_size]
                
                # First message includes header
                if i == 0:
                    legacy_content = "# 📚 Legacy Book Clubs\n\n*These channels were created manually and are not managed by the bot.*\n\n"
                else:
                    legacy_content = ""
                
                for manual_club in chunk:
                    try:
                        channel = await guild.fetch_channel(manual_club['channel_id'])
                        legacy_content += f"📘 **{manual_club['name']}** - <#{channel.id}>\n"
                    except:
                        legacy_content += f"📘 **{manual_club['name']}** - *(channel not found)*\n"
                
                if needs_recreate or len(message_ids) <= legacy_msg_index:
                    msg_legacy = await directory_channel.send(legacy_content)
                    if len(message_ids) <= legacy_msg_index:
                        message_ids.append(msg_legacy.id)
                    else:
                        message_ids[legacy_msg_index] = msg_legacy.id
                else:
                    # Edit existing message
                    try:
                        msg_legacy = await directory_channel.fetch_message(message_ids[legacy_msg_index])
                        await msg_legacy.edit(content=legacy_content)
                    except:
                        # Message was deleted, recreate
                        msg_legacy = await directory_channel.send(legacy_content)
                        message_ids[legacy_msg_index] = msg_legacy.id
                
                legacy_msg_index += 1
        
        # Save the message IDs
        directory_channels[guild.id]['message_ids'] = message_ids
        if 'message_id' in directory_channels[guild.id]:
            del directory_channels[guild.id]['message_id']  # Remove old format
        save_directories()
        
    except Exception as e:
        print(f"Error updating book club directory: {e}")

    """Update the live discussion guide, splitting into multiple messages if needed"""
    if not book_club.guide_message_ids:
        return
    
    try:
        channel = await guild.fetch_channel(book_club.channel_id)
        guide_content = await generate_guide_content(book_club, guild)
        
        # Split content into chunks of ~1900 characters (leaving buffer for safety)
        chunks = split_into_chunks(guide_content, 1900)
        
        # Update existing messages or create new ones
        for i, chunk in enumerate(chunks):
            if i < len(book_club.guide_message_ids):
                # Update existing message
                try:
                    msg = await channel.fetch_message(book_club.guide_message_ids[i])
                    await msg.edit(content=chunk)
                except:
                    # If message was deleted, create a new one
                    new_msg = await channel.send(chunk)
                    book_club.guide_message_ids[i] = new_msg.id
            else:
                # Create new message for additional chunks
                new_msg = await channel.send(chunk)
                book_club.guide_message_ids.append(new_msg.id)
        
        # Delete extra messages if content got shorter
        if len(chunks) < len(book_club.guide_message_ids):
            for i in range(len(chunks), len(book_club.guide_message_ids)):
                try:
                    msg = await channel.fetch_message(book_club.guide_message_ids[i])
                    await msg.delete()
                except:
                    pass
            book_club.guide_message_ids = book_club.guide_message_ids[:len(chunks)]
    
    except Exception as e:
        print(f"Error updating discussion guide: {e}")

def split_into_chunks(text, max_length):
    """Split text into chunks at chapter boundaries when possible"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    lines = text.split('\n')
    
    for line in lines:
        # If adding this line would exceed limit
        if len(current_chunk) + len(line) + 1 > max_length:
            # If current chunk is not empty, save it
            if current_chunk:
                chunks.append(current_chunk.rstrip())
                current_chunk = ""
            
            # If single line is too long, split it
            if len(line) > max_length:
                # Split long line into words
                words = line.split(' ')
                for word in words:
                    if len(current_chunk) + len(word) + 1 > max_length:
                        chunks.append(current_chunk.rstrip())
                        current_chunk = word + " "
                    else:
                        current_chunk += word + " "
            else:
                current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.rstrip())
    
    # Wrap each chunk in spoiler tags
    wrapped_chunks = [f"||{chunk}||" for chunk in chunks]
    
    return wrapped_chunks

@bot.tree.command(name="create_bookclub", description="Create a new book club channel and threads")
async def create_bookclub(interaction: discord.Interaction):
    """Interactive command to create a book club"""
    await interaction.response.send_message("Let's set up your book club! I'll ask you some questions in this channel.", ephemeral=True)
    
    user = interaction.user
    channel = interaction.channel
    
    def check(m):
        return m.author == user and m.channel == channel
    
    try:
        # Get book name
        await channel.send(f"{user.mention} What's the name of the book?")
        book_msg = await bot.wait_for('message', check=check, timeout=120.0)
        book_name = book_msg.content
        
        # Get chapter information
        await channel.send("Enter chapters in format: 'Prologue, 1-5, Epilogue' (supports text, numbers, or ranges)")
        chapters_msg = await bot.wait_for('message', check=check, timeout=120.0)
        chapter_input = chapters_msg.content
        
        # Parse the chapter string
        chapters = parse_chapters(chapter_input)
        
        # Get members
        await channel.send("Mention all members who should have access (mention them with @, separated by spaces). Example: @user1 @user2 @user3")
        members_msg = await bot.wait_for('message', check=check, timeout=180.0)
        members = members_msg.mentions
        
        if not members:
            await channel.send("No valid members mentioned. Aborting.")
            return
        
        # Create the book club
        await channel.send(f"Creating book club for **{book_name}** with {len(chapters)} chapters and {len(members)} members...")
        
        # Create text channel in the same category as the current channel
        guild = interaction.guild
        category = interaction.channel.category if hasattr(interaction.channel, 'category') else None
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add permissions for selected members
        for member in members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        book_channel = await guild.create_text_channel(
            name=book_name.lower().replace(' ', '-'),
            overwrites=overwrites,
            category=category
        )
        
        # Send welcome message
        await book_channel.send(f"**Welcome to the {book_name} Book Club!**\n\nThreads for each chapter will appear below. Happy reading!")
        
        # Create threads for each chapter
        thread_ids = {}
        thread_objects = {}  # Store thread objects for navigation links
        
        for chapter in chapters:
            # Create a message for the thread
            msg = await book_channel.send(f"**{chapter}**")
            thread = await msg.create_thread(name=chapter)
            
            # Add members to thread
            for member in members:
                try:
                    await thread.add_user(member)
                except:
                    pass
            
            thread_ids[chapter] = thread.id
            thread_objects[chapter] = thread
        
        # Now add navigation messages to each thread
        chapter_list = list(chapters)
        for i, chapter in enumerate(chapter_list):
            thread = thread_objects[chapter]
            
            # Build navigation message
            nav_parts = []
            
            # Previous chapter link
            if i > 0:
                prev_chapter = chapter_list[i - 1]
                prev_thread_id = thread_ids[prev_chapter]
                nav_parts.append(f"← Previous: <#{prev_thread_id}>")
            
            # Next chapter link
            if i < len(chapter_list) - 1:
                next_chapter = chapter_list[i + 1]
                next_thread_id = thread_ids[next_chapter]
                nav_parts.append(f"Next: <#{next_thread_id}> →")
            
            if nav_parts:
                nav_message = " | ".join(nav_parts)
                await thread.send(nav_message)
        
        # Create initial discussion guide message
        guide_msg = await book_channel.send(f"# Discussion Guide: {book_name}\n||*No comments yet. The guide will update automatically as people comment!*||")
        
        # Store book club data
        book_club_id = f"{guild.id}_{book_channel.id}"
        book_clubs[book_club_id] = BookClub(
            guild.id,
            book_name,
            book_channel.id,
            thread_ids,
            [m.id for m in members],
            chapters,
            [guide_msg.id],
            False,  # is_archived
            user.id  # creator_id
        )
        
        # Save to file
        save_book_clubs()
        
        # Update the book club directory
        await update_book_club_list(guild)
        
        await channel.send(f"✅ Book club created! Check out {book_channel.mention}")
        
    except asyncio.TimeoutError:
        await channel.send("Setup timed out. Please try again.")
    except ValueError:
        await channel.send("Invalid input. Please use the command again and enter a valid number.")
    except Exception as e:
        await channel.send(f"An error occurred: {str(e)}")

@bot.tree.command(name="sync_commands", description="Force re-sync all bot commands with Discord")
async def sync_commands(interaction: discord.Interaction):
    """Force re-sync all commands with Discord"""
    await interaction.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Re-synced {len(synced)} command(s) with Discord. Changes may take a few minutes to appear.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error syncing commands: {str(e)}", ephemeral=True)

@bot.tree.command(name="set_directory", description="Set this channel as the book club directory")
async def set_directory(interaction: discord.Interaction):
    """Set the current channel as the book club directory"""
    guild = interaction.guild
    channel = interaction.channel
    
    # Set this channel as the directory
    directory_channels[guild.id] = {
        'channel_id': channel.id,
        'message_ids': []
    }
    save_directories()
    
    # Create/update the directory list
    await update_book_club_list(guild)
    
    await interaction.response.send_message(f"✅ This channel is now the book club directory!", ephemeral=True)

@bot.tree.command(name="set_archive_category", description="Set a category for archiving old book clubs")
async def set_archive_category(interaction: discord.Interaction, category: discord.CategoryChannel):
    """Set the category where archived book clubs will be moved"""
    guild = interaction.guild
    
    # Store the archive category
    archive_categories[guild.id] = category.id
    save_archive_categories()
    
    await interaction.response.send_message(f"✅ Book clubs will be archived to **{category.name}**!", ephemeral=True)

@bot.tree.command(name="set_active_category", description="Set a category for active book clubs")
async def set_active_category(interaction: discord.Interaction, category: discord.CategoryChannel):
    """Set the category where active book clubs should be placed"""
    guild = interaction.guild
    
    # We'll store active categories similar to archive categories
    if not hasattr(bot, 'active_categories'):
        bot.active_categories = {}
    
    bot.active_categories[guild.id] = category.id
    
    # Save to a file
    active_file = 'active_categories.json'
    with open(active_file, 'w') as f:
        json.dump(bot.active_categories, f, indent=2)
    
    await interaction.response.send_message(f"✅ Active book clubs will be moved to **{category.name}**!", ephemeral=True)

@bot.tree.command(name="archive_bookclub", description="Archive this book club (moves to Old Books category)")
async def archive_bookclub(interaction: discord.Interaction):
    """Archive the current book club"""
    # Check if current channel is a book club
    book_club_id = f"{interaction.guild.id}_{interaction.channel.id}"
    if book_club_id not in book_clubs:
        await interaction.response.send_message("This command must be used in a book club channel.", ephemeral=True)
        return
    
    # Check if archive category is set
    if interaction.guild.id not in archive_categories:
        await interaction.response.send_message("No archive category set! Use `/set_archive_category` first.", ephemeral=True)
        return
    
    book_club = book_clubs[book_club_id]
    
    try:
        # Get the archive category
        archive_category = await interaction.guild.fetch_channel(archive_categories[interaction.guild.id])
        
        # Move the channel to the archive category
        await interaction.channel.edit(category=archive_category)
        
        # Mark as archived
        book_club.is_archived = True
        save_book_clubs()
        
        # Update the directory
        await update_book_club_list(interaction.guild)
        
        await interaction.response.send_message(f"✅ Book club archived and moved to **{archive_category.name}**!", ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"Error archiving book club: {str(e)}", ephemeral=True)

@bot.tree.command(name="unarchive_bookclub", description="Unarchive a book club (moves back to active)")
async def unarchive_bookclub(interaction: discord.Interaction, channel: discord.TextChannel):
    """Unarchive a book club and move it back to active"""
    await interaction.response.defer(ephemeral=True)
    
    # Check if specified channel is a book club
    book_club_id = f"{interaction.guild.id}_{channel.id}"
    if book_club_id not in book_clubs:
        await interaction.followup.send("That channel is not a book club.", ephemeral=True)
        return
    
    book_club = book_clubs[book_club_id]
    
    # Check if it's actually archived
    if not book_club.is_archived:
        await interaction.followup.send("This book club is already active!", ephemeral=True)
        return
    
    try:
        # Load active categories if not already loaded
        if not hasattr(bot, 'active_categories'):
            bot.active_categories = {}
            active_file = 'active_categories.json'
            if os.path.exists(active_file):
                with open(active_file, 'r') as f:
                    data = json.load(f)
                    bot.active_categories = {int(k): int(v) for k, v in data.items()}
        
        # Check if active category is set
        if interaction.guild.id in bot.active_categories:
            # Move to active category
            active_category = await interaction.guild.fetch_channel(bot.active_categories[interaction.guild.id])
            await channel.edit(category=active_category)
            message = f"✅ Book club unarchived and moved to **{active_category.name}**!"
        else:
            # No active category set, just unarchive without moving
            message = "✅ Book club unarchived! (Use `/set_active_category` to automatically move unarchived books to a specific category)"
        
        # Mark as not archived
        book_club.is_archived = False
        save_book_clubs()
        
        # Update the directory
        await update_book_club_list(interaction.guild)
        
        await interaction.followup.send(message, ephemeral=True)
    
    except Exception as e:
        await interaction.followup.send(f"Error unarchiving book club: {str(e)}", ephemeral=True)

@bot.tree.command(name="import_legacy_books", description="Import all channels from a category as legacy book clubs")
async def import_legacy_books(interaction: discord.Interaction, category: discord.CategoryChannel):
    """Import all text channels from a category as legacy (manually created) book clubs"""
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    
    # Get all text channels in the category
    channels_in_category = [ch for ch in category.channels if isinstance(ch, discord.TextChannel)]
    
    if not channels_in_category:
        await interaction.followup.send(f"No text channels found in **{category.name}**.", ephemeral=True)
        return
    
    # Initialize manual book clubs list for this guild if it doesn't exist
    if guild.id not in manual_book_clubs:
        manual_book_clubs[guild.id] = []
    
    # Add each channel to the manual book clubs list
    imported_count = 0
    for channel in channels_in_category:
        # Check if already in manual list
        already_exists = any(bc['channel_id'] == channel.id for bc in manual_book_clubs[guild.id])
        if not already_exists:
            manual_book_clubs[guild.id].append({
                'name': channel.name.replace('-', ' ').title(),
                'channel_id': channel.id
            })
            imported_count += 1
    
    # Save to file
    save_manual_book_clubs()
    
    # Update the directory
    await update_book_club_list(guild)
    
    await interaction.followup.send(
        f"✅ Imported {imported_count} legacy book club(s) from **{category.name}**!\n"
        f"They will appear in the directory under 'Legacy Book Clubs'.",
        ephemeral=True
    )

@bot.tree.command(name="join_bookclub", description="Join an active book club")
async def join_bookclub(interaction: discord.Interaction):
    """Join an active book club by selecting from a list"""
    # Get all active book clubs for this guild
    guild_book_clubs = [bc for bc in book_clubs.values() if bc.guild_id == interaction.guild.id and not bc.is_archived]
    
    if not guild_book_clubs:
        await interaction.response.send_message("No active book clubs available to join.", ephemeral=True)
        return
    
    # Sort by book name
    guild_book_clubs.sort(key=lambda x: x.book_name)
    
    # Create a dropdown with book club options (max 25 for Discord select menus)
    if len(guild_book_clubs) > 25:
        await interaction.response.send_message(
            "There are too many book clubs to display in a menu. Please use `/add_member` with a specific channel.",
            ephemeral=True
        )
        return
    
    # Create select menu options
    from discord import SelectOption
    from discord.ui import Select, View
    
    options = []
    book_club_map = {}
    for i, bc in enumerate(guild_book_clubs):
        # Check if user is already a member
        is_member = interaction.user.id in bc.members
        label = bc.book_name
        if is_member:
            label += " ✓"
        
        options.append(SelectOption(
            label=label[:100],  # Discord max label length
            description=f"{len(bc.chapters)} chapters" + (" - Already joined" if is_member else ""),
            value=str(i)
        ))
        book_club_map[str(i)] = bc
    
    # Create the select menu
    select = Select(
        placeholder="Choose a book club to join...",
        options=options
    )
    
    async def select_callback(select_interaction):
        selected_index = select.values[0]
        selected_bc = book_club_map[selected_index]
        
        # Check if already a member
        if select_interaction.user.id in selected_bc.members:
            await select_interaction.response.send_message(
                f"You're already a member of **{selected_bc.book_name}**!",
                ephemeral=True
            )
            return
        
        # Add the user to the book club
        try:
            channel = await interaction.guild.fetch_channel(selected_bc.channel_id)
            
            # Add permissions to channel
            await channel.set_permissions(select_interaction.user, read_messages=True, send_messages=True)
            
            # Add to all threads
            for thread_id in selected_bc.thread_ids.values():
                try:
                    thread = await interaction.guild.fetch_channel(thread_id)
                    await thread.add_user(select_interaction.user)
                except:
                    pass
            
            selected_bc.members.append(select_interaction.user.id)
            save_book_clubs()
            
            await select_interaction.response.send_message(
                f"✅ You've joined **{selected_bc.book_name}**! Check out {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await select_interaction.response.send_message(
                f"Error joining book club: {str(e)}",
                ephemeral=True
            )
    
    select.callback = select_callback
    view = View()
    view.add_item(select)
    
    await interaction.response.send_message(
        "Select a book club to join:",
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="add_member", description="Add a member to a book club")
async def add_member(interaction: discord.Interaction, channel: discord.TextChannel, member: discord.Member):
    """Add a member to a book club"""
    await interaction.response.defer(ephemeral=True)
    
    # Check if specified channel is a book club
    book_club_id = f"{interaction.guild.id}_{channel.id}"
    if book_club_id not in book_clubs:
        await interaction.followup.send("That channel is not a book club.", ephemeral=True)
        return
    
    book_club = book_clubs[book_club_id]
    
    # Check if member is already in the book club
    if member.id in book_club.members:
        await interaction.followup.send(f"{member.mention} is already in this book club.", ephemeral=True)
        return
    
    # Add permissions to channel
    await channel.set_permissions(member, read_messages=True, send_messages=True)
    
    # Add to all threads
    for thread_id in book_club.thread_ids.values():
        try:
            thread = await interaction.guild.fetch_channel(thread_id)
            await thread.add_user(member)
        except:
            pass
    
    book_club.members.append(member.id)
    
    # Save to file
    save_book_clubs()
    
    await interaction.followup.send(f"✅ Added {member.mention} to {channel.mention}!", ephemeral=True)

# Run the bot
# Replace 'YOUR_BOT_TOKEN' with your actual Discord bot token
bot.run('YOUR_BOT_TOKEN')