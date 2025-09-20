import discord
from discord.ext import commands
import asyncio
import os
import tempfile
from datetime import datetime
import logging

# Import your video generator (assuming it's saved as video_generator.py)
try:
    from video_generator import create_welcome_video
except ImportError:
    print("Error: Make sure video_generator.py is in the same directory!")
    exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot settings
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for member join events

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None
)

# Welcome settings
welcome_channels = {}  # {guild_id: channel_id}
background_image = "bg.png"  # Your background image

@bot.event
async def on_ready():
    """Called when bot is ready"""
    logger.info(f'{bot.user} has landed!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Loaded commands: {[cmd.name for cmd in bot.commands]}')
    logger.info('------')
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for new members 👋"
        )
    )

@bot.event
async def on_message(message):
    """Debug function to see if bot can read messages"""
    # Don't respond to own messages
    if message.author == bot.user:
        return
    
    # Debug: print all messages the bot sees
    logger.info(f"Bot saw message: '{message.content}' from {message.author}")
    
    # Check if it's a command
    if message.content.startswith('!'):
        logger.info(f"Command detected: {message.content}")
    
    # Process commands (VERY IMPORTANT!)
    try:
        await bot.process_commands(message)
        logger.info("Commands processed successfully")
    except Exception as e:
        logger.error(f"Error processing commands: {e}")

@bot.event
async def on_member_join(member):
    """Called when a new member joins the server"""
    guild = member.guild
    
    # Check if welcome channel is set for this guild
    if guild.id not in welcome_channels:
        logger.info(f"No welcome channel set for {guild.name}")
        return
    
    channel_id = welcome_channels[guild.id]
    channel = guild.get_channel(channel_id)
    
    if not channel:
        logger.error(f"Welcome channel {channel_id} not found in {guild.name}")
        return
    
    # Check permissions
    if not channel.permissions_for(guild.me).send_messages:
        logger.error(f"No permission to send messages in {channel.name}")
        return
    
    if not channel.permissions_for(guild.me).attach_files:
        logger.error(f"No permission to attach files in {channel.name}")
        return
    
    await send_welcome_video(channel, member)

async def send_welcome_video(channel, member):
    """Generate and send welcome video"""
    try:
        # Show typing indicator
        async with channel.typing():
            logger.info(f"Creating welcome video for {member.display_name}")
            
            # Create unique filename to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"welcome_{member.id}_{timestamp}.mp4"
            
            # Generate video in a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                video_path = os.path.join(temp_dir, video_filename)
                
                # Create the welcome video
                await asyncio.to_thread(
                    create_welcome_video,
                    username=member.display_name,
                    output_file=video_path,
                    bg_image=background_image if os.path.exists(background_image) else None,
                    cleanup=True,
                    verbose=False
                )
                
                # Send the video
                if os.path.exists(video_path):
                    file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
                    logger.info(f"Video created: {file_size:.2f} MB")
                    
                    # Discord file size limit check (25MB for most servers)
                    if file_size > 24:
                        await channel.send(f"🎉 Welcome {member.mention}! (Video too large to send)")
                        logger.warning(f"Video too large: {file_size:.2f} MB")
                        return
                    
                    # Create embed for additional welcome message
                    embed = discord.Embed(
                        title="🎉 Welcome to the Server!",
                        description=f"Hey {member.mention}, welcome to **{channel.guild.name}**!",
                        color=0x00ff41  # Matrix green
                    )
                    embed.add_field(
                        name="📋 Getting Started",
                        value="• Be respectful\n• Share with everyone\n• Have fun!",
                        inline=False
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text=f"Member #{channel.guild.member_count}")
                    
                    # Send video and embed
                    with open(video_path, 'rb') as video_file:
                        discord_file = discord.File(video_file, filename=f"welcome_{member.display_name}.mp4")
                        await channel.send(file=discord_file, embed=embed)
                    
                    logger.info(f"Welcome video sent for {member.display_name}")
                else:
                    # Fallback if video creation fails
                    await channel.send(f"🎉 Welcome {member.mention} to **{channel.guild.name}**!")
                    logger.error("Video file not found after creation")
    
    except Exception as e:
        logger.error(f"Error creating welcome video for {member.display_name}: {e}")
        # Send simple welcome message as fallback
        try:
            await channel.send(f"🎉 Welcome {member.mention} to **{channel.guild.name}**!")
        except Exception as fallback_error:
            logger.error(f"Even fallback message failed: {fallback_error}")

@bot.command(name='ping')
async def ping(ctx):
    """Simple test command"""
    logger.info(f"Ping command called by {ctx.author}")
    await ctx.send("🏓 Pong!")

@bot.command(name='setwelcome')
@commands.has_permissions(manage_guild=True)
async def set_welcome_channel(ctx, channel: discord.TextChannel = None):
    """Set the welcome channel for this server"""
    logger.info(f"setwelcome command called by {ctx.author}")
    
    if channel is None:
        channel = ctx.channel
    
    # Check bot permissions in the channel
    permissions = channel.permissions_for(ctx.guild.me)
    if not permissions.send_messages or not permissions.attach_files:
        await ctx.send("❌ I need permission to send messages and attach files in that channel!")
        return
    
    welcome_channels[ctx.guild.id] = channel.id
    
    embed = discord.Embed(
        title="✅ Welcome Channel Set!",
        description=f"Welcome videos will now be sent to {channel.mention}",
        color=0x00ff41
    )
    await ctx.send(embed=embed)
    
    logger.info(f"Welcome channel set to {channel.name} in {ctx.guild.name}")

@bot.command(name='testwelcome')
@commands.has_permissions(manage_guild=True)
async def test_welcome(ctx):
    """Test the welcome message with your own user"""
    logger.info(f"testwelcome command called by {ctx.author}")
    
    if ctx.guild.id not in welcome_channels:
        await ctx.send("❌ No welcome channel set! Use `!setwelcome` first.")
        return
    
    channel_id = welcome_channels[ctx.guild.id]
    channel = ctx.guild.get_channel(channel_id)
    
    if not channel:
        await ctx.send("❌ Welcome channel not found!")
        return
    
    await ctx.send("🔄 Creating test welcome video...")
    await send_welcome_video(channel, ctx.author)

@bot.command(name='welcomestatus')
async def welcome_status(ctx):
    """Check welcome bot status"""
    guild_id = ctx.guild.id
    
    embed = discord.Embed(
        title="🤖 Welcome Bot Status",
        color=0x00ff41
    )
    
    if guild_id in welcome_channels:
        channel = ctx.guild.get_channel(welcome_channels[guild_id])
        channel_name = channel.mention if channel else "❌ Channel not found"
        embed.add_field(name="Welcome Channel", value=channel_name, inline=False)
    else:
        embed.add_field(name="Welcome Channel", value="❌ Not set", inline=False)
    
    bg_status = "✅ Found" if os.path.exists(background_image) else "❌ Missing"
    embed.add_field(name="Background Image", value=f"{bg_status} ({background_image})", inline=False)
    
    embed.add_field(name="Member Count", value=ctx.guild.member_count, inline=True)
    embed.add_field(name="Bot Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='help')
async def help_command(ctx):
    """Show help message"""
    logger.info(f"help command called by {ctx.author}")
    
    embed = discord.Embed(
        title="🎬 Welcome Video Bot Commands",
        description="Create epic terminal-style welcome videos for new members!",
        color=0x00ff41
    )
    
    embed.add_field(
        name="🛠️ Admin Commands",
        value="`!setwelcome [#channel]` - Set welcome channel\n"
              "`!testwelcome` - Test welcome video\n"
              "`!welcomestatus` - Check bot status",
        inline=False
    )
    
    embed.add_field(
        name="👋 How it Works",
        value="• New members get an awesome typing animation video\n"
              "• Terminal-style green text with your background\n"
              "• Automatic cleanup of temporary files",
        inline=False
    )
    
    embed.add_field(
        name="📋 Setup Requirements",
        value="• Bot needs `Send Messages` and `Attach Files` permissions\n"
              "• Place your background image as `bg.png` in bot directory\n"
              "• Use `!setwelcome` to set welcome channel",
        inline=False
    )
    
    embed.set_footer(text="Bot created Toshith for epic welcomes!")
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Command error: {error}")
    logger.error(f"Error type: {type(error)}")
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
        logger.info("Permission error occurred")
    elif isinstance(error, commands.CommandNotFound):
        logger.info(f"Command not found: {ctx.message.content}")
        await ctx.send(f"❌ Command not found. Try `!help`")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument!")
        logger.info("Missing argument error")
    else:
        logger.error(f"Unhandled command error: {error}")
        await ctx.send(f"❌ Something went wrong: {error}")

if __name__ == "__main__":
    # Configuration
    TOKEN = ""
    
    if not TOKEN:
        print("❌ Please set DISCORD_BOT_TOKEN environment variable!")
        print("Example: export DISCORD_BOT_TOKEN='your_bot_token_here'")
        exit(1)
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    
    # Check if background image exists
    if os.path.exists("bg.png"):
        print("✅ Background image found")
    else:
        print("⚠️  Background image (bg.png) not found - videos will use black background")
    
    # Check video generator
    try:
        from video_generator import create_welcome_video
        print("✅ Video generator imported successfully")
    except ImportError as e:
        print(f"❌ Could not import video generator: {e}")
        print("Make sure video_generator.py is in the same directory!")
        exit(1)
    
    print("🚀 Starting Welcome Bot...")
    
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Invalid bot token!")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")