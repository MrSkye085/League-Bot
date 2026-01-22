import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import string
import os
import datetime

THEME_COLOR = discord.Color.default() 
DATA_FILE = "data.json"
WARN_FILE = "data.json"
RANK_FILE = "data.json" 

LEAGUE_HOST_ROLE_ID =  
STAFF_ROLE_ID = 
PING_ROLE_ID =
ANNOUNCEMENT_CHANNEL_ID =  
RANK_ANNOUNCEMENT_CHANNEL_ID = 
WARN_LOG_CHANNEL_ID = 

HOST_STRIKE_1_ROLE_ID = 
HOST_STRIKE_2_ROLE_ID = 
HOST_STRIKE_3_ROLE_ID = 
STRIKE_ROLES = [HOST_STRIKE_1_ROLE_ID, HOST_STRIKE_2_ROLE_ID, HOST_STRIKE_3_ROLE_ID]

REGION_CHOICES = ["EU", "NA", "ASIA", "SA"]
GAMEMODE_CHOICES = ["Swift Game", "War Game"]
MATCHTYPE_CHOICES = ["4v4", "3v3", "2v2", "1v1"]
PERKS_CHOICES = ["Enabled", "Disabled"]

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

bot = commands.Bot(command_prefix="?", intents=intents, help_command=None, activity=discord.Game(name="/help | Dev: Skye"), status=discord.Status.idle)

@bot.event
async def on_ready():
    await bot.tree.sync()
    data = load_league_data()
    for league_id, league_data in data.items():
        if 'announcement_msg_id' in league_data:
            required_rank_id = league_data.get("rank_required_id") 
            bot.add_view(JoinButtonView(league_id, required_rank_id))
            
    print("Persistent views loaded.")

@bot.tree.command(name="set-rank", description="Map a Discord Role to a Rank Name, Color, and Level.")
@app_commands.describe(
    role="The Discord Role to map to a Rank.",
    rank_name="The display name of the rank (e.g., Diamond I).",
    level="The numerical level of the rank (Higher is better, e.g., Gold=uncement_msg_id": announcement_msg.id, 
        "announcement_channel_id": announcement_channel.id,
        "thread_id": thread.id,
        "thread_msg_id": thread_msg.id,
        "rank_required_id": required_rank_id 
    }
    data[str(league_id)] = league_data
    save_league_data(data)
    
    await interaction.followup.send(f"{league_type_label} League **{league_id}** hosted successfully! Check {announcement_channel.mention} for the join message.", ephemeral=True)

@host_league.autocomplete('region')
async def region_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return await autocomplete_handler(interaction, current, REGION_CHOICES)

@host_league.autocomplete('game_mode')
async def gamemode_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return await autocomplete_handler(interaction, current, GAMEMODE_CHOICES)

@host_league.autocomplete('match_type')
async def matchtype_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return await autocomplete_handler(interaction, current, MATCHTYPE_CHOICES)

@host_league.autocomplete('perks')
async def perks_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return await autocomplete_handler(interaction, current, PERKS_CHOICES)

@bot.tree.command(name="add-member", description="Add a member to your league")
@app_commands.describe(member="Member to add", league_id="League ID (Optional if run in thread)")
async def add_member(interaction: discord.Interaction, member: discord.Member, league_id: str = None):
    await interaction.response.defer(ephemeral=True)
    
    if not is_league_host(interaction):
        await interaction.followup.send("Only League Hosts can add members.", ephemeral=True)
        return

    league_id, league, data = await get_league_info(interaction, league_id)

    if not league:
        await interaction.followup.send("League not found. Please specify the `league_id` or run the command inside the league's private thread.", ephemeral=True)
        return
        
    if interaction.user.id != league["host"]:
        await interaction.followup.send("You can only add members to the league you are hosting.", ephemeral=True)
        return

    required_rank_id = league.get("rank_required_id", None)
    
    if required_rank_id and required_rank_id != "None":
        if not is_player_eligible(member, required_rank_id):
            rank_data = load_rank_data()
            required_rank_name = rank_data.get(required_rank_id, {}).get('name', 'N/A')
            
            await interaction.followup.send(
                f"Cannot add {member.mention}. This league requires a minimum rank of **{required_rank_name}** or higher.", 
                ephemeral=True
            )
            return
        
    if member.id in league["players"]:
        await interaction.followup.send(f"{member.mention} is already in the league **{league_id}**.", ephemeral=True)
        return

    league["players"].append(member.id)
    save_league_data(data)
    
    thread_id = league.get("thread_id")
    thread_channel = interaction.guild.get_channel(thread_id)
    
    if not thread_channel and thread_id:
        try:
            thread_channel = await interaction.guild.fetch_channel(thread_id)
        except Exception:
            pass

    if thread_channel and isinstance(thread_channel, discord.Thread):
        try:
            await thread_channel.add_user(member)
            await send_join_notification(thread_channel, member, league_id, is_host_add=True)
            await interaction.followup.send(f"{member.mention} has been added to the league **{league_id}** and the coordination thread.", ephemeral=False)
        except Exception:
            await interaction.followup.send(f"Warning: {member.mention} has been added to the league **{league_id}**, but failed to add them to the thread and send notification.", ephemeral=False)
    else:
        await interaction.followup.send(f"{member.mention} has been added to the league **{league_id}**. Warning: Thread not found.", ephemeral=False)


@bot.tree.command(name="kick-member", description="Kick a member from your league")
@app_commands.describe(member="Member to kick", league_id="League ID (Optional if run in thread)")
async def kick_member(interaction: discord.Interaction, member: discord.Member, league_id: str = None):
    await interaction.response.defer(ephemeral=True)

    if not is_league_host(interaction):
        await interaction.followup.send("Only League Hosts can kick members.", ephemeral=True)
        return
    
    league_id, league, data = await get_league_info(interaction, league_id)

    if not league:
        await interaction.followup.send("League not found. Please specify the `league_id` or run the command inside the league's private thread.", ephemeral=True)
        return
        
    if interaction.user.id != league["host"]:
        await interaction.followup.send("You can only kick members from the league you are hosting.", ephemeral=True)
        return

    if member.id not in league["players"]:
        await interaction.followup.send(f"{member.mention} is not in the league **{league_id}**.", ephemeral=True)
        return
    
    if member.id == league["host"]:
        await interaction.followup.send("You cannot kick the host. Use /end-league if you wish to close the league.", ephemeral=True)
        return

    league["players"].remove(member.id)
    save_league_data(data)
    
    thread_id = league.get("thread_id")
    thread_channel = interaction.guild.get_channel(thread_id)
    
    if not thread_channel and thread_id:
        try:
            thread_channel = await interaction.guild.fetch_channel(thread_id)
        except Exception:
            pass

    if thread_channel and isinstance(thread_channel, discord.Thread):
        try:
            await thread_channel.remove_user(member)
            await thread_channel.send(f"{member.mention} was kicked from the league.")
            await interaction.followup.send(f"{member.mention} has been kicked from the league **{league_id}** and removed from the coordination thread.", ephemeral=False)
        except Exception:
            await interaction.followup.send(f"Warning: {member.mention} has been kicked from the league **{league_id}**, but failed to remove them from the thread.", ephemeral=False)
    else:
        await interaction.followup.send(f"{member.mention} has been kicked from the league **{league_id}**. Warning: Thread not found.", ephemeral=False)


@bot.tree.command(name="leave-league", description="Leave a league")
@app_commands.describe(league_id="League ID (Optional if run in thread)")
async def leave_league(interaction: discord.Interaction, league_id: str = None):
    await interaction.response.defer(ephemeral=True)
    
    league_id, league, data = await get_league_info(interaction, league_id)

    if not league:
        await interaction.followup.send("League not found. Please specify the `league_id` or run the command inside the league's private thread.", ephemeral=True)
        return

    if interaction.user.id not in league["players"]:
        await interaction.followup.send("You are not part of this league.", ephemeral=True)
        return

    if interaction.user.id == league['host']:
        await interaction.followup.send("As the host, you cannot manually leave. Please use /end-league to close the league.", ephemeral=True)
        return

    league["players"].remove(interaction.user.id)
    save_league_data(data)

    thread_id = league.get("thread_id")
    thread_channel = interaction.guild.get_channel(thread_id)

    if not thread_channel and thread_id:
        try:
            thread_channel = await interaction.guild.fetch_channel(thread_id)
        except Exception:
            pass

    if thread_channel and isinstance(thread_channel, discord.Thread):
        try:
            await thread_channel.remove_user(interaction.user)
            await thread_channel.send(f"{interaction.user.mention} has left the league.")
            await interaction.followup.send(f"You have left league **{league_id}** and been removed from the thread.", ephemeral=False)
        except Exception:
            await interaction.followup.send(f"Warning: You have left league **{league_id}**, but failed to remove you from the thread.", ephemeral=False)
    else:
        await interaction.followup.send(f"You have left league **{league_id}**. Warning: Thread not found.", ephemeral=False)


@bot.tree.command(name="status", description="Get status of a league")
@app_commands.describe(league_id="League ID (Optional if run in thread)")
async def status(interaction: discord.Interaction, league_id: str = None):
    await interaction.response.defer()
    
    league_id, league, data = await get_league_info(interaction, league_id)

    if not league:
        await interaction.followup.send("League not found. Please specify the `league_id` or run the command inside the league's private thread.", ephemeral=True)
        return

    try:
        team_size = int(league['match_type'].split('v')[0])
        players_required = team_size * 2
    except (IndexError, ValueError):
        players_required = 0
        
    required_rank_id = league.get("rank_required_id")
    rank_restriction_text = "None (Open)"
    if required_rank_id and required_rank_id != "None":
        rank_data = load_rank_data()
        rank_restriction_text = rank_data.get(required_rank_id, {}).get('name', f'Role ID: {required_rank_id}')

    members = [f"<@{m}>" for m in league["players"]]
    embed = discord.Embed(
        title=f"League **{league_id}** Status",
        description=f"**{len(members)}** / **{players_required}** players joined.",
        color=THEME_COLOR
    )
    embed.add_field(name="Host", value=f"<@{league['host']}>", inline=False)
    embed.add_field(name="Players", value=", ".join(members) if members else "No players yet", inline=False)
    embed.add_field(name="Game Mode", value=league["game_mode"], inline=True)
    embed.add_field(name="Match Type", value=league["match_type"], inline=True)
    embed.add_field(name="Perks", value=league["perks"], inline=True)
    embed.add_field(name="Min Rank Required", value=rank_restriction_text, inline=True)
    if league["private_link"]:
        embed.add_field(name="Private Server Link", value=league["private_link"], inline=False)
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="randomize-teams", description="Randomly split joined players into two teams (2v2, 3v3, 4v4 only)")
@app_commands.describe(league_id="League ID (Optional if run in thread)")
async def randomize_teams(interaction: discord.Interaction, league_id: str = None):
    await interaction.response.defer()

    if not is_league_host(interaction):
        await interaction.followup.send("Only League Hosts can randomize teams.", ephemeral=True)
        return
        
    league_id, league, data = await get_league_info(interaction, league_id)

    if not league:
        await interaction.followup.send("League not found. Please specify the `league_id` or run the command inside the league's private thread.", ephemeral=True)
        return
        
    if interaction.user.id != league["host"]:
        await interaction.followup.send("You can only randomize teams for the league you are hosting.", ephemeral=True)
        return

    match_type = league.get("match_type")
    
    if match_type == "1v1":
        await interaction.followup.send("Team randomization is not available for 1v1 leagues.", ephemeral=True)
        return
    
    try:
        team_size = int(match_type.split('v')[0])
        players_required = team_size * 2
    except (IndexError, ValueError):
        await interaction.followup.send(f"Could not determine team size from match type: `{match_type}`.", ephemeral=True)
        return

    all_players = league["players"].copy()
    
    if len(all_players) < players_required:
        await interaction.followup.send(f"Cannot randomize: You need {players_required} players to start, but only have {len(all_players)}.", ephemeral=True)
        return
    
    random.shuffle(all_players)
    
    team_a = all_players[:team_size]
    team_b = all_players[team_size:players_required]
    
    team_a_mentions = [f"<@{uid}>" for uid in team_a]
    team_b_mentions = [f"<@{uid}>" for uid in team_b]
    
    embed = discord.Embed(
        title="Teams Randomized!",
        description=f"Match Type: **{match_type}** | Players Used: **{players_required}**",
        color=THEME_COLOR
    )
    embed.add_field(name="Team 1", value="\n".join(team_a_mentions), inline=True)
    embed.add_field(name="Team 2", value="\n".join(team_b_mentions), inline=True)
    
    thread_channel = interaction.guild.get_channel(league.get("thread_id"))
    
    if thread_channel and isinstance(thread_channel, discord.Thread):
        await thread_channel.send(f"Randomized teams ready! Host: {interaction.user.mention}", embed=embed)
        await interaction.followup.send(f"Teams randomized and sent to the private thread: {thread_channel.mention}", ephemeral=True)
    else:
        await interaction.followup.send(f"Teams randomized. Please check the results below, as the private thread could not be found.", embed=embed, ephemeral=False)


@bot.tree.command(name="end-league", description="End a league and clean up")
@app_commands.describe(league_id="League ID (Optional if run in thread)")
async def end_league(interaction: discord.Interaction, league_id: str = None):
    await interaction.response.defer()
    
    league_id, league, data = await get_league_info(interaction, league_id)

    if not league:
        await interaction.followup.send("League not found. Please specify the `league_id` or run the command inside the league's private thread.", ephemeral=True)
        return

    if interaction.user.id != league["host"] and not is_staff(interaction):
        await interaction.followup.send("You must be the league host or staff to end this league.", ephemeral=True)
        return
    
    channel = bot.get_channel(league.get("announcement_channel_id"))
    msg_id = league.get("announcement_msg_id")

    if channel and msg_id:
        try:
            message = await channel.fetch_message(msg_id)
            await message.edit(view=None) 
        except discord.NotFound:
            print(f"Announcement message {msg_id} not found.")
        except Exception as e:
            print(f"Error editing announcement message view: {e}")
            await interaction.followup.send(f"Warning: League ended, but failed to disable the join button. Error: `{e}`", ephemeral=True)
            
        ended_embed = discord.Embed(
            title=f"Kada League Has Ended",
            description=f"This league, hosted by <@{league['host']}>, has ended. Check has results in <#1442196085601861632>.",
            color=THEME_COLOR
        )
        ended_embed.set_footer(text=f"ID: {league_id} | Ended by {interaction.user.display_name}")
        try:
            await channel.send(embed=ended_embed)
        except Exception as e:
            print(f"Error sending end announcement: {e}")


    thread = interaction.guild.get_channel(league.get("thread_id"))
    if not thread and league.get("thread_id"):
        try:
            thread = await interaction.guild.fetch_channel(league["thread_id"])
        except Exception:
            pass
            
    if thread:
        try:
            await thread.delete()
        except Exception as e:
            print(f"Error deleting thread: {e}")

    data.pop(league_id)
    save_league_data(data)

    embed = discord.Embed(
        title=f"League {league_id} Ended",
        description="This league has officially ended, the join button has been disabled, and the private thread was deleted.",
        color=THEME_COLOR
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="warn", description="Issue a strike to a host user and track their warnings.")
@app_commands.describe(
    target="The host user to receive the strike.", 
    reason="The reason for the strike."
)
async def warn_user(interaction: discord.Interaction, target: discord.Member, reason: str):
    await interaction.response.defer()
    
    if not is_staff(interaction):
        await interaction.followup.send("Only staff can use the warning system.", ephemeral=True)
        return
    
    warn_data = load_warn_data()
    target_id_str = str(target.id)
    current_warn_count = warn_data.get(target_id_str, 0) + 1
    warn_data[target_id_str] = current_warn_count
    save_warn_data(warn_data)
    
    host_role = interaction.guild.get_role(LEAGUE_HOST_ROLE_ID)
    strike_role_to_add = interaction.guild.get_role(get_strike_role_id(current_warn_count))
    action_log = ""
    
    if current_warn_count >= 3:
        roles_to_remove_all = [r for r in target.roles if r.id in STRIKE_ROLES]
        if roles_to_remove_all:
             await target.remove_roles(*roles_to_remove_all, reason=f"Final Strike ({current_warn_count}) reached.")
             
        if host_role in target.roles:
            try:
                await target.remove_roles(host_role, reason=f"Maximum strikes reached ({current_warn_count}). Host role revoked.")
                action_log = f"**{target.mention}'s Host Role was REVOKED.** (Strike {current_warn_count} reached)."
            except discord.Forbidden:
                action_log = f"**Host Role REVOKE FAILED** for {target.mention} (Bot lacks permissions)."
        else:
            action_log = f"**{target.mention}'s Host Strike {current_warn_count} recorded.** (No Host role to revoke)."
        
    elif strike_role_to_add:
        roles_to_remove_prev = [r for r in target.roles if r.id in STRIKE_ROLES and r.id != strike_role_to_add.id]
        if roles_to_remove_prev:
            await target.remove_roles(*roles_to_remove_prev, reason=f"Strike {current_warn_count} issued.")
            
        if strike_role_to_add not in target.roles:
            try:
                await target.add_roles(strike_role_to_add, reason=f"Strike {current_warn_count} issued by {interaction.user.name}.")
                action_log = f"**Assigned role: {strike_role_to_add.name}** to {target.mention}."
            except discord.Forbidden:
                action_log = f"**Role ADDITION FAILED** for {target.mention} (Bot lacks permissions)."
        else:
             action_log = f"**{target.mention} already has {strike_role_to_add.name}.**"

    log_channel = bot.get_channel(WARN_LOG_CHANNEL_ID)
    log_status = ""
    
    log_embed = discord.Embed(
        title=f"Strike Issued: #{current_warn_count}",
        color=THEME_COLOR,
        timestamp=interaction.created_at
    )
    log_embed.add_field(name="Target", value=target.mention, inline=True)
    log_embed.add_field(name="Total Strikes", value=str(current_warn_count), inline=True)
    log_embed.add_field(name="Staff Member", value=interaction.user.mention, inline=True)
    log_embed.add_field(name="Reason", value=reason, inline=False)
    log_embed.add_field(name="Action", value=action_log if action_log else "Warning logged, no role action.", inline=False)
    log_embed.set_footer(text=f"Target ID: {target.id}")

    if log_channel:
        try:
            await log_channel.send(embed=log_embed)
            log_status = f"Warning logged to {log_channel.mention}."
        except discord.Forbidden:
            log_status = "Warning could NOT be logged (Missing permissions in log channel)."
        except Exception:
            log_status = "Warning could NOT be logged (Log channel error)."
    else:
        log_status = f"Warning Log Channel (ID: `{WARN_LOG_CHANNEL_ID}`) not found."
    
    await interaction.followup.send(
        f"**Strike #{current_warn_count}** issued to **{target.mention}** for: **{reason}**." 
        f"\n{action_log}\n\n*{log_status}*", 
        ephemeral=False
    )

@bot.tree.command(name="help", description="Show all commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="League Bot Commands",
        description="Here are the commands for managing leagues and moderation:",
        color=THEME_COLOR
    )
    embed.add_field(name="/host-league", value="Host a new league. Now features **rank hierarchy** for restrictions.", inline=False)
    embed.add_field(name="/randomize-teams", value="Randomly split joined players into two teams (2v2, 3v3, 4v4 only).", inline=False)
    embed.add_field(name="/add-member", value="Add a member to your hosted league (Respects minimum rank requirements).", inline=False)
    embed.add_field(name="/kick-member", value="Kick a member from your hosted league.", inline=False)
    embed.add_field(name="/leave-league", value="Leave a league.", inline=False)
    embed.add_field(name="/status", value="Check status and players of a league.", inline=False)
    embed.add_field(name="/end-league", value="End a league, disable the join button, and delete the thread.", inline=False)
    embed.add_field(name="/warn", value="Issue a Host Strike to a user (Host Strike system only. Staff only).", inline=False)
    embed.add_field(name="/moderate", value="[STAFF] Apply a moderation action (Kick, Ban, Timeout) to a user.", inline=False)
    embed.add_field(name="/set-rank", value="Map a Discord role to a specific Rank Name, Color, and **Level** (for hierarchy checks).", inline=False)
    embed.add_field(name="/rank-list", value="View all configured rank roles and their levels.", inline=False)
   
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run("")
