import discord
from discord.ext import commands
import asyncio
import random
import re
from datetime import datetime, timedelta
import aiohttp
import os

# ================= CONFIG =================
OWNER_ID = 123456789012345678  # 🔴 APNA DISCORD ID DAALE
PARTY_EMOJI = discord.PartialEmoji(name="Party", id=1458109878370570446)

# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# ================= NO PREFIX SYSTEM =================
noprefix_users = set()

async def get_prefix(bot, message):
    if message.author.id in noprefix_users:
        return commands.when_mentioned_or("")(bot, message)
    return commands.when_mentioned_or("!", "?")(bot, message)

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

# ================= DATA =================
afk_users = {}
ended_giveaways = set()

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ================= NO PREFIX COMMANDS =================
@bot.command()
async def addnp(ctx, user: discord.User):
    if ctx.author.id != 951842341621211166:
        return await ctx.send("❌ Only owner can use this.")
    noprefix_users.add(user.id)
    await ctx.send(f"✅ No-prefix enabled for {user.mention}")

@bot.command()
async def removenp(ctx, user: discord.User):
    if ctx.author.id != 951842341621211166:
        return await ctx.send("❌ Only owner can use this.")
    noprefix_users.discard(user.id)
    await ctx.send(f"❌ No-prefix removed for {user.mention}")

# ================= AFK =================
@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"💤 {ctx.author.mention} is AFK: **{reason}**")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"👋 Welcome back {message.author.mention}")

    for user in message.mentions:
        if user.id in afk_users:
            await message.channel.send(
                f"💤 {user.mention} is AFK: **{afk_users[user.id]}**"
            )

    await bot.process_commands(message)

# ================= MODERATION =================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int, *, reason="Muted"):
    until = datetime.utcnow() + timedelta(minutes=minutes)
    await member.timeout(until, reason=reason)
    await ctx.send(f"🔇 Muted {member.mention} for {minutes} minutes")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Deleted {len(deleted)-1} messages", delete_after=5)

# ================= GIVEAWAY =================
def parse_time(time_str):
    match = re.match(r"(\d+)(s|m|h|d)$", time_str.lower())
    if not match:
        return None
    amount, unit = match.groups()
    return int(amount) * {"s":1,"m":60,"h":3600,"d":86400}[unit]

@bot.command()
@commands.has_permissions(administrator=True)
async def gw(ctx, time: str, winners: int, *, prize: str):
    seconds = parse_time(time)
    if not seconds:
        return await ctx.send("❌ Invalid time format")

    end_time = datetime.utcnow() + timedelta(seconds=seconds)
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=(
            f"**Prize:** {prize}\n"
            f"**Winners:** {winners}\n"
            f"**Ends:** <t:{int(end_time.timestamp())}:R>\n"
            f"**Host:** {ctx.author.mention}\n\n"
            f"React with 🎉 to enter!"
        ),
        color=discord.Color.purple()
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction(PARTY_EMOJI)

    await asyncio.sleep(seconds)
    if msg.id not in ended_giveaways:
        await end_giveaway(ctx.channel, msg.id)

async def end_giveaway(channel, message_id, reroll=False):
    if not reroll:
        ended_giveaways.add(message_id)

    msg = await channel.fetch_message(message_id)
    reaction = discord.utils.get(msg.reactions, emoji=PARTY_EMOJI)
    users = [u async for u in reaction.users() if not u.bot]

    if not users:
        return await channel.send("❌ No participants")

    winner = random.choice(users)
    embed = msg.embeds[0]
    embed.add_field(name="🏆 Winner", value=winner.mention, inline=False)
    await msg.edit(embed=embed)

    text = "🔁 Rerolled Winner" if reroll else "🎉 Giveaway Ended"
    await channel.send(f"{text}: {winner.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def gend(ctx, message_id: int):
    await end_giveaway(ctx.channel, message_id)

@bot.command()
@commands.has_permissions(administrator=True)
async def reroll(ctx, message_id: int):
    await end_giveaway(ctx.channel, message_id, reroll=True)

# ================= VC =================
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("🔊 Joined VC")
    else:
        await ctx.send("❌ Join VC first")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and after.channel is None:
        for vc in member.guild.voice_channels:
            if vc.permissions_for(member.guild.me).connect:
                await vc.connect()
                break

# ================= START =================
TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
