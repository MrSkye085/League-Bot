import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import string
import os
import datetime

THEME_COLOR = discord.Color.default() 
DATA_FILE = "leagues.json"
WARN_FILE = "warns.json"
RANK_FILE = "ranks.json" 

LEAGUE_HOST_ROLE_ID = 1413192727780266054 
STAFF_ROLE_ID = 1412240496452960308 
ANNOUNCEMENT_CHANNEL_ID = 1425143359470702816 
RANK_ANNOUNCEMENT_CHANNEL_ID = 1443653105303683186 
WARN_LOG_CHANNEL_ID = 1425143357721805013 
MOD_LOG_CHANNEL_ID = 1425143357721805013 
HOST_STRIKE_1_ROLE_ID = 1428441303451963524 
HOST_STRIKE_2_ROLE_ID = 1428441333139247219 
HOST_STRIKE_3_ROLE_ID = 1428441348578476367 
STRIKE_ROLES = [HOST_STRIKE_1_ROLE_ID, HOST_STRIKE_2_ROLE_ID, HOST_STRIKE_3_ROLE_ID]

REGION_CHOICES = ["EU", "NA", "ASIA", "SA"]
GAMEMODE_CHOICES = ["Swift Game", "War Game"]
MATCHTYPE_CHOICES = ["4v4", "3v3", "2v2", "1v1"]
PERKS_CHOICES = ["Enabled", "Disabled"]
MOD_ACTION_CHOICES = ["Kick", "Ban", "Timeout"] 

snipe_data = {}
afk_data = {}

def load_data(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} 

def save_data(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def load_league_data(): return load_data(DATA_FILE)
def save_league_data(data): save_data(data, DATA_FILE)
def load_warn_data(): return load_data(WARN_FILE) 
def save_warn_data(data): save_data(data, WARN_FILE) 
def load_rank_data(): return load_data(RANK_FILE)
def save_rank_data(data): save_data(data, RANK_FILE)

if not os.path.exists(DATA_FILE): save_league_data({})
if not os.path.exists(WARN_FILE): save_warn_data({})
if not os.path.exists(RANK_FILE): save_rank_data({})

def generate_league_id():
    return ''.join(random.choices(string.digits, k=20))

def is_league_host(interaction: discord.Interaction):
    role = discord.utils.get(interaction.user.roles, id=LEAGUE_HOST_ROLE_ID)
    return role is not None

def is_staff(target):
    if isinstance(target, discord.Interaction):
        member = target.user
    elif isinstance(target, commands.Context):
        member = target.author
    else:
        member = target 
        
    if isinstance(member, discord.Member):
        return discord.utils.get(member.roles, id=STAFF_ROLE_ID) is not None
    return False

def get_strike_role_id(count):
    if count == 1:
        return HOST_STRIKE_1_ROLE_ID
    elif count == 2:
        return HOST_STRIKE_2_ROLE_ID
    elif count == 3:
        return HOST_STRIKE_3_ROLE_ID
    return None

async def log_action(ctx, action: str, target: discord.User | discord.Member, reason: str, details: str = None):
    guild = ctx.guild if hasattr(ctx, 'guild') else ctx.command.cog.bot.get_guild(ctx.guild_id)
    if not guild:
        print("Could not retrieve guild for logging.")
        return

    log_channel = guild.get_channel(MOD_LOG_CHANNEL_ID)
    if not log_channel:
        return

    moderator = ctx.author if hasattr(ctx, 'author') else ctx.user
    
    embed = discord.Embed(
        title=f"MOD LOG: {action}",
        color=THEME_COLOR,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="User", value=f"{target.mention} ({target.id})", inline=True)
    embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})", inline=True)
    channel_mention = ctx.channel.mention if hasattr(ctx, 'channel') and hasattr(ctx.channel, 'mention') else "N/A"
    embed.add_field(name="Channel", value=channel_mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    
    if details:
        embed.add_field(name="Details", value=details, inline=False)

    try:
        await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to send mod log: {e}")

async def get_league_info(interaction: discord.Interaction, league_id: str = None):
    data = load_league_data()
    
    if not league_id:
        if isinstance(interaction.channel, discord.Thread):
            for lid, league in data.items():
                if str(league.get("thread_id")) == str(interaction.channel_id):
                    league_id = lid
                    break
    
    if league_id and league_id in data:
        return league_id, data[league_id], data
    
    return None, None, data

def get_member_highest_rank_level(member: discord.Member) -> int:
    rank_data = load_rank_data()
    highest_level = 0
    member_role_ids = {role.id for role in member.roles}
    
    for role_id_str, rank_config in rank_data.items():
        role_id = int(role_id_str)
        
        if role_id in member_role_ids:
            level = rank_config.get('level', 0)
            if level > highest_level:
                highest_level = level
            
    return highest_level

def get_rank_details(member: discord.Member) -> tuple[str, discord.Color]:
    rank_data = load_rank_data()
    highest_rank_name = "Unranked"
    highest_rank_color = THEME_COLOR
    highest_level = 0
    
    member_role_ids = {role.id for role in member.roles}
    
    for role_id_str, rank_config in rank_data.items():
        role_id = int(role_id_str)
        
        if role_id in member_role_ids:
            level = rank_config.get('level', 0)
            if level > highest_level:
                highest_level = level
                highest_rank_name = rank_config['name']
                hex_code = rank_config.get('color', '#808080')
                try:
                    highest_rank_color = discord.Color(int(hex_code.lstrip('#'), 16))
                except ValueError:
                    highest_rank_color = THEME_COLOR
            
    return highest_rank_name, highest_rank_color

async def send_join_notification(thread_channel: discord.Thread, member: discord.Member, league_id: str, is_host_add: bool = False):
    rank_name, rank_color = get_rank_details(member)
    
    action_source = "Host added" if is_host_add else "Joined via button"
    
    embed = discord.Embed(
        title="Player Joined League",
        description=f"**{member.mention}** has been added to the league!",
        color=THEME_COLOR
    )
    embed.set_author(name=f"{member.display_name} | Rank: {rank_name}", icon_url=member.display_avatar.url)
    embed.add_field(name="League ID", value=league_id, inline=True)
    embed.add_field(name="Source", value=action_source, inline=True)
    embed.set_footer(text="Good luck!")
    
    try:
        await thread_channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to send join notification to thread {thread_channel.id}: {e}")

def is_player_eligible(member: discord.Member, required_rank_id: str | None) -> bool:
    if required_rank_id is None:
        return True
    
    rank_data = load_rank_data()
    required_level = rank_data.get(required_rank_id, {}).get('level', 0)

    if required_level == 0 and required_rank_id != "None":
        return False

    member_highest_level = get_member_highest_rank_level(member)
    
    return member_highest_level >= required_level

def get_rank_role_choices() -> list[app_commands.Choice[str]]:
    rank_data = load_rank_data()
    choices = [app_commands.Choice(name="None (Open League)", value="None")]
    
    sorted_ranks = sorted(rank_data.items(), key=lambda item: item[1].get('level', 0), reverse=True)
    
    for role_id_str, config in sorted_ranks:
        name = config.get('name', config.get('role_name', f"Rank {role_id_str}"))
        level = config.get('level', 0)
        if level > 0:
            choices.append(app_commands.Choice(name=f"Min Rank: {name}", value=role_id_str))
            
    return choices

class JoinButtonView(discord.ui.View):
    def __init__(self, league_id, required_rank_id: str | None):
        super().__init__(timeout=None) 
        self.league_id = league_id
        self.required_rank_id = required_rank_id if required_rank_id != "None" else None

    @discord.ui.button(label="Join League", style=discord.ButtonStyle.blurple, custom_id="join_league_btn")
    async def join_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        member = interaction.user

        if self.required_rank_id is not None:
            if not is_player_eligible(member, self.required_rank_id):
                rank_data = load_rank_data()
                required_rank_name = rank_data.get(self.required_rank_id, {}).get('name', 'N/A')
                
                await interaction.followup.send(
                    f"This league requires a minimum rank of **{required_rank_name}** or higher.\n"
                    "Your highest current rank does not meet this requirement.", 
                    ephemeral=True
                )
                return

        data = load_league_data()
        league_id = self.league_id

        if league_id not in data:
            await interaction.followup.send("This league no longer exists.", ephemeral=True)
            return
        
        league = data[league_id]
        
        try:
            players_required = int(league['match_type'].split('v')[0]) * 2
        except (IndexError, ValueError):
            players_required = 0 

        if players_required != 0 and len(league["players"]) >= players_required:
            await interaction.followup.send("This league is full!", ephemeral=True)
            return

        if member.id in league["players"]:
            await interaction.followup.send("You are already in this league.", ephemeral=True)
            return

        league["players"].append(member.id)
        save_league_data(data)
        
        thread_id = league.get("thread_id")
        thread_channel = interaction.guild.get_channel(thread_id)
        thread_status = ""
        
        if not thread_channel and thread_id:
            try:
                thread_channel = await interaction.guild.fetch_channel(thread_id)
            except discord.NotFound:
                thread_channel = None
            except Exception as e:
                print(f"Error fetching thread {thread_id}: {e}")
                thread_channel = None

        if thread_channel and isinstance(thread_channel, discord.Thread):
            try:
                await thread_channel.add_user(member)
                await send_join_notification(thread_channel, member, league_id, is_host_add=False)
                thread_status = f"You have been added to the private thread: {thread_channel.mention}."
            except discord.Forbidden:
                thread_status = "Could not add you to the thread (Bot lacks permissions)."
            except Exception as e:
                thread_status = f"Error adding you to the thread: {e}"
        else:
            thread_status = "Warning: Could not find the league's private thread."

        await interaction.followup.send(
            f"You have joined League **{league_id}**! ({len(league['players'])}/{players_required} players)\n\n"
            f"{thread_status}",
            ephemeral=True
        )

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

bot = commands.Bot(command_prefix="?", intents=intents)

@bot.event
async def on_ready():
    activity = discord.Game(name="?help in Kada")
    await bot.change_presence(status=discord.Status.idle, activity=activity)
    
    await bot.tree.sync()
    print(f"{bot.user} is online and ready with prefix '?'!")
    
    data = load_league_data()
    for league_id, league_data in data.items():
        if 'announcement_msg_id' in league_data:
            required_rank_id = league_data.get("rank_required_id") 
            bot.add_view(JoinButtonView(league_id, required_rank_id))
            
    print("Persistent views loaded.")

@bot.event
async def on_message_delete(message):
    global snipe_data
    if message.author.bot:
        return
    snipe_data[message.channel.id] = {
        "content": message.content,
        "author": message.author,
        "time": message.created_at
    }

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.mentions:
        for member in message.mentions:
            if str(member.id) in afk_data:
                afk_info = afk_data[str(member.id)]
                afk_time = afk_info['time']
                if afk_time.tzinfo is None:
                    afk_time = afk_time.replace(tzinfo=datetime.timezone.utc)
                    
                time_diff = (datetime.datetime.now(datetime.timezone.utc) - afk_time).seconds
                
                if time_diff < 60:
                    time_ago = f"{time_diff} seconds"
                elif time_diff < 3600:
                    time_ago = f"{time_diff // 60} minutes"
                elif time_diff < 86400:
                    time_ago = f"{time_diff // 3600} hours"
                else:
                    time_ago = f"{time_diff // 86400} days"
                
                embed = discord.Embed(
                    title="AFK Alert",
                    description=f"{member.mention} is AFK: **{afk_info['reason']}**\n(Been AFK for **{time_ago}**)",
                    color=THEME_COLOR
                )
                await message.channel.send(embed=embed)
    
    if str(message.author.id) in afk_data:
        afk_info = afk_data.pop(str(message.author.id))
        
        afk_time = afk_info['time']
        if afk_time.tzinfo is None:
            afk_time = afk_time.replace(tzinfo=datetime.timezone.utc)
            
        embed = discord.Embed(
            title="Welcome Back!",
            description=f"{message.author.mention}, your AFK status has been removed.",
            color=THEME_COLOR
        )
        await message.channel.send(embed=embed)

    await bot.process_commands(message)

async def autocomplete_handler(interaction: discord.Interaction, current: str, choices_list: list) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in choices_list if current.lower() in choice.lower()
    ][:25] 
    
async def rank_role_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    choices = get_rank_role_choices()
    return [
        choice for choice in choices 
        if current.lower() in choice.name.lower() or current == choice.value
    ][:25]

@bot.command(name="ban")
@commands.has_role(STAFF_ROLE_ID)
async def ban_user(ctx, member: discord.User, *, reason="No reason provided"):
    if isinstance(member, discord.Member) and member.top_role >= ctx.author.top_role:
        response = "I cannot ban this user as their highest role is equal to or higher than yours."
    else:
        try:
            await ctx.guild.ban(member, reason=f"{ctx.author.name}: {reason}")
            response = f"Successfully banned **{member}** ({member.id})."
            await log_action(ctx, "BAN", member, reason)
        except discord.Forbidden:
            response = "I do not have the required permissions to ban this user."
        except discord.HTTPException as e:
            response = f"Failed to ban user: {e}"
            
    embed = discord.Embed(title="Ban Command", description=response, color=THEME_COLOR)
    embed.add_field(name="Target", value=member.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="unban")
@commands.has_role(STAFF_ROLE_ID)
async def unban_user(ctx, user_id: int, *, reason="No reason provided"):
    try:
        user = discord.Object(id=user_id)
        await ctx.guild.unban(user, reason=f"{ctx.author.name}: {reason}")
        
        unbanned_user = await bot.fetch_user(user_id)
        
        response = f"Successfully unbanned **{unbanned_user.name}** ({user_id})."
        await log_action(ctx, "UNBAN", unbanned_user, reason)
        
        embed = discord.Embed(title="Unban Command", description=response, color=THEME_COLOR)
        embed.add_field(name="Target ID", value=str(user_id), inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        await ctx.send(embed=embed)

    except discord.NotFound:
        response = f"User ID `{user_id}` not found in the ban list."
        embed = discord.Embed(title="Unban Failed", description=response, color=discord.Color.red())
        embed.add_field(name="Target ID", value=str(user_id), inline=True)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        response = "I do not have the required permissions to unban users."
        embed = discord.Embed(title="Unban Failed", description=response, color=discord.Color.red())
        embed.add_field(name="Target ID", value=str(user_id), inline=True)
        await ctx.send(embed=embed)
    except Exception as e:
        response = f"An error occurred: {e}"
        embed = discord.Embed(title="Unban Failed", description=response, color=discord.Color.red())
        embed.add_field(name="Target ID", value=str(user_id), inline=True)
        await ctx.send(embed=embed)

@bot.group(name="role", invoke_without_command=True)
@commands.has_role(STAFF_ROLE_ID)
async def role_group(ctx):
    embed = discord.Embed(
        title="Role Management",
        description="Use `?role toggle <user> <role>` to add or remove a role.",
        color=THEME_COLOR
    )
    embed.add_field(name="Usage Example", value="`?role toggle @User#1234 @RoleName`", inline=True)
    await ctx.send(embed=embed)

@role_group.command(name="toggle")
@commands.has_role(STAFF_ROLE_ID)
async def role_toggle(ctx, member: discord.Member, *, role: discord.Role):
    if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        response = "You cannot manage roles that are equal to or higher than your highest role."
        color = discord.Color.red()
    elif role >= ctx.guild.me.top_role:
        response = "I cannot manage this role as it is equal to or higher than my highest role."
        color = discord.Color.red()
    else:
        try:
            if role in member.roles:
                await member.remove_roles(role, reason=f"Role removed by {ctx.author.name} (toggle).")
                response = f"Removed **{role.name}** from {member.mention}."
                action = "ROLE_REMOVE"
                color = THEME_COLOR
            else:
                await member.add_roles(role, reason=f"Role added by {ctx.author.name} (toggle).")
                response = f"Added **{role.name}** to {member.mention}."
                action = "ROLE_ADD"
                color = THEME_COLOR
            
            await log_action(ctx, action, member, f"Role: {role.name}", details=response)

        except discord.Forbidden:
            response = "I do not have permissions to manage that role."
            color = discord.Color.red()
        except Exception as e:
            response = f"An error occurred: {e}"
            color = discord.Color.red()

    embed = discord.Embed(title="Role Toggle", description=response, color=color)
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Role", value=role.mention, inline=True)
    await ctx.send(embed=embed)


bot.command(name="mute", aliases=["timeout"])
@commands.has_role(STAFF_ROLE_ID)
async def mute_user(ctx, member: discord.Member, duration: str, *, reason="No reason provided"):
    time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    
    if not any(unit in duration for unit in time_units):
        embed = discord.Embed(
            title="Mute Failed",
            description="Invalid duration format. Use: `<number>s/m/h/d` (e.g., `30m` for 30 minutes).",
            color=discord.Color.red()
        )
        embed.add_field(name="Example", value="`?mute @User 3h Breaking rules`", inline=True)
        retur
