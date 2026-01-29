async def update_discussion_guide(book_club, guild):
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
        
        save_book_clubs()
    
    except Exception as e:
        print(f"Error updating discussion guide: {e}")
import discord
from discord.ext import commands
import asyncio
import json
import os

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Store book club data
book_clubs = {}
directory_channels = {}  # {guild_id: {'channel_id': id, 'message_id': id}}
archive_categories = {}  # {guild_id: category_id}
manual_book_clubs = {}  # {guild_id: [{'name': str, 'channel_id': int}]}
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
            'is_archived': book_club.is_archived
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
                    bc_data.get('is_archived', False)
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
    def __init__(self, guild_id, book_name, channel_id, thread_ids, members, chapters, guide_message_ids=None, is_archived=False):
        self.guild_id = guild_id
        self.book_name = book_name
        self.channel_id = channel_id
        self.thread_ids = thread_ids
        self.members = members
        self.chapters = chapters
        self.guide_message_ids = guide_message_ids or []
        self.is_archived = is_archived

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
    
    # Header outside spoiler, content inside spoiler
    header = f"# Discussion Guide: {book_club.book_name}\n"
    spoiler_content = "\n".join(guide_parts)
    return f"{header}||{spoiler_content}||"

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
    
    # Generate list content
    list_content = ""
    
    # Active book clubs section
    list_content += "# 📚 Active Book Clubs\n\n"
    if active_clubs:
        for book_club in sorted(active_clubs, key=lambda x: x.book_name):
            try:
                channel = await guild.fetch_channel(book_club.channel_id)
                list_content += f"📖 **{book_club.book_name}** - {channel.mention}\n"
            except:
                list_content += f"📖 **{book_club.book_name}** - *(channel not found)*\n"
    else:
        list_content += "*No active book clubs. Use `/create_bookclub` to start one!*\n"
    
    # Past book clubs section
    if archived_clubs:
        list_content += "\n# 📕 Past Book Clubs\n\n"
        for book_club in sorted(archived_clubs, key=lambda x: x.book_name):
            try:
                channel = await guild.fetch_channel(book_club.channel_id)
                list_content += f"📕 **{book_club.book_name}** - {channel.mention}\n"
            except:
                list_content += f"📕 **{book_club.book_name}** - *(channel not found)*\n"
    
    # Manual book clubs section (not managed by bot)
    if guild.id in manual_book_clubs and manual_book_clubs[guild.id]:
        list_content += "\n# 📚 Legacy Book Clubs\n\n*These channels were created manually and are not managed by the bot.*\n\n"
        for manual_club in sorted(manual_book_clubs[guild.id], key=lambda x: x['name']):
            try:
                channel = await guild.fetch_channel(manual_club['channel_id'])
                list_content += f"📘 **{manual_club['name']}** - {channel.mention}\n"
            except:
                list_content += f"📘 **{manual_club['name']}** - *(channel not found)*\n"
    
    # Update or create the directory message
    try:
        if 'message_id' in directory_info and directory_info['message_id']:
            # Update existing message
            try:
                list_msg = await directory_channel.fetch_message(directory_info['message_id'])
                await list_msg.edit(content=list_content)
            except:
                # Message was deleted, create new one
                list_msg = await directory_channel.send(list_content)
                directory_channels[guild.id]['message_id'] = list_msg.id
                save_directories()
        else:
            # Create new directory message
            list_msg = await directory_channel.send(list_content)
            directory_channels[guild.id]['message_id'] = list_msg.id
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
    
    return chunks

@bot.tree.command(name="create_bookclub", description="Create a new book club channel and threads")
async def create_bookclub(interaction: discord.Interaction):
    """Interactive command to create a book club"""
    await interaction.response.send_message("Let's set up your book club! I'll ask you some questions.", ephemeral=True)
    
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
            
            await thread.send(f"Discussion thread for **{chapter}**. Share your thoughts here!")
            thread_ids[chapter] = thread.id
        
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
            [guide_msg.id]
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

@bot.tree.command(name="set_directory", description="Set this channel as the book club directory")
async def set_directory(interaction: discord.Interaction):
    """Set the current channel as the book club directory"""
    guild = interaction.guild
    channel = interaction.channel
    
    # Set this channel as the directory
    directory_channels[guild.id] = {
        'channel_id': channel.id,
        'message_id': None
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

@bot.tree.command(name="unarchive_bookclub", description="Unarchive this book club (moves back to active)")
async def unarchive_bookclub(interaction: discord.Interaction):
    """Unarchive the current book club and move it back to active"""
    # Check if current channel is a book club
    book_club_id = f"{interaction.guild.id}_{interaction.channel.id}"
    if book_club_id not in book_clubs:
        await interaction.response.send_message("This command must be used in a book club channel.", ephemeral=True)
        return
    
    book_club = book_clubs[book_club_id]
    
    # Check if it's actually archived
    if not book_club.is_archived:
        await interaction.response.send_message("This book club is already active!", ephemeral=True)
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
            await interaction.channel.edit(category=active_category)
            message = f"✅ Book club unarchived and moved to **{active_category.name}**!"
        else:
            # No active category set, just unarchive without moving
            message = "✅ Book club unarchived! (Use `/set_active_category` to automatically move unarchived books to a specific category)"
        
        # Mark as not archived
        book_club.is_archived = False
        save_book_clubs()
        
        # Update the directory
        await update_book_club_list(interaction.guild)
        
        await interaction.response.send_message(message, ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"Error unarchiving book club: {str(e)}", ephemeral=True)

@bot.tree.command(name="import_legacy_books", description="Import all channels from a category as legacy book clubs")
async def import_legacy_books(interaction: discord.Interaction, category: discord.CategoryChannel):
    """Import all text channels from a category as legacy (manually created) book clubs"""
    guild = interaction.guild
    
    # Get all text channels in the category
    channels_in_category = [ch for ch in category.channels if isinstance(ch, discord.TextChannel)]
    
    if not channels_in_category:
        await interaction.response.send_message(f"No text channels found in **{category.name}**.", ephemeral=True)
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
    
    await interaction.response.send_message(
        f"✅ Imported {imported_count} legacy book club(s) from **{category.name}**!\n"
        f"They will appear in the directory under 'Legacy Book Clubs'.",
        ephemeral=True
    )

@bot.tree.command(name="add_member", description="Add a member to this book club")
async def add_member(interaction: discord.Interaction, member: discord.Member):
    """Add a new member to the book club in the current channel"""
    # Check if current channel is a book club
    book_club_id = f"{interaction.guild.id}_{interaction.channel.id}"
    if book_club_id not in book_clubs:
        await interaction.response.send_message("This command must be used in a book club channel.", ephemeral=True)
        return
    
    book_club = book_clubs[book_club_id]
    
    # Check if member is already in the book club
    if member.id in book_club.members:
        await interaction.response.send_message(f"{member.mention} is already in this book club.", ephemeral=True)
        return
    
    # Add permissions to channel
    await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
    
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
    
    await interaction.response.send_message(f"✅ Added {member.mention} to the book club!", ephemeral=True)

# Run the bot
# Replace 'YOUR_BOT_TOKEN' with your actual Discord bot token
bot.run('YOUR_BOT_TOKEN')