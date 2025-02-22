import asyncio
import logging
import sqlite3
from typing import cast

import discord
from discord.ext import commands
import wavelink

# Bot Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN"
LAVALINK_URI = "http://localhost:2333"
LAVALINK_PASSWORD = "youshallnotpass"

# Initialize SQLite Database
conn = sqlite3.connect("favorites.db")
cursor = conn.cursor()
cursor.execute(
    """CREATE TABLE IF NOT EXISTS favorites (
        user_id INTEGER,
        song_title TEXT,
        song_author TEXT,
        song_url TEXT
    )"""
)
conn.commit()

# Logging Setup
logging.basicConfig(level=logging.INFO)

# Discord Bot Setup
class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        nodes = [wavelink.Node(uri=LAVALINK_URI, password=LAVALINK_PASSWORD)]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

    async def on_ready(self):
        logging.info(f"✅ Logged in as {self.user} | ID: {self.user.id}")

bot = MusicBot()

# ===== MUSIC COMMANDS =====
@bot.command()
async def play(ctx: commands.Context, *, query: str):
    """Plays a song from YouTube."""
    if not ctx.author.voice:
        return await ctx.send("🚨 Please join a voice channel first!")

    player: wavelink.Player = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
    player.autoplay = wavelink.AutoPlayMode.enabled

    tracks = await wavelink.Playable.search(query)
    if not tracks:
        return await ctx.send("❌ No results found.")

    track = tracks[0]
    await player.queue.put_wait(track)

    if player.playing:
        await ctx.send(f"🎵 Added **{track.title}** to the queue.")
    else:
        await player.play(track, volume=30)

@bot.command()
async def queue(ctx: commands.Context):
    """Displays the current queue."""
    player: wavelink.Player = ctx.voice_client
    if not player or not player.queue:
        return await ctx.send("🎶 The queue is empty.")

    queue_list = "\n".join([f"**{track.title}** by `{track.author}`" for track in player.queue])
    await ctx.send(f"📜 **Queue:**\n{queue_list}")

@bot.command()
async def skip(ctx: commands.Context):
    """Skips the current song."""
    player: wavelink.Player = ctx.voice_client
    if not player or not player.playing:
        return await ctx.send("⚠️ No song is currently playing.")

    await ctx.send(f"⏭️ Skipped **{player.current.title}**.")
    await player.skip(force=True)

@bot.command()
async def disconnect(ctx: commands.Context):
    """Disconnects the bot from the voice channel."""
    player: wavelink.Player = ctx.voice_client
    if player:
        await player.disconnect()
        await ctx.message.add_reaction("✅")

# ===== FAVORITES COMMANDS =====
@bot.command()
async def favorite(ctx: commands.Context):
    """Adds the current playing song to favorites."""
    player: wavelink.Player = ctx.voice_client
    if not player or not player.current:
        return await ctx.send("⚠️ No song is currently playing.")

    track = player.current
    user_id = ctx.author.id
    song_title, song_author, song_url = track.title, track.author, track.uri

    cursor.execute(
        "INSERT INTO favorites (user_id, song_title, song_author, song_url) VALUES (?, ?, ?, ?)",
        (user_id, song_title, song_author, song_url)
    )
    conn.commit()

    await ctx.send(f"💾 Added **{song_title}** by **{song_author}** to your favorites.")

@bot.command()
async def favorites(ctx: commands.Context):
    """Lists the user's favorite songs."""
    cursor.execute("SELECT song_title, song_author, song_url FROM favorites WHERE user_id = ?", (ctx.author.id,))
    rows = cursor.fetchall()

    if not rows:
        await ctx.send("❤️ You don't have any favorite songs yet.")
    else:
        favorites_list = "\n".join([f"**{title}** by `{author}` - [Link]({url})" for title, author, url in rows])
        await ctx.send(f"💾 **Your Favorites:**\n{favorites_list}")

# ===== FILTER COMMANDS =====
@bot.command()
async def nightcore(ctx: commands.Context):
    """Applies a Nightcore effect."""
    player: wavelink.Player = ctx.voice_client
    if player:
        filters = player.filters
        filters.timescale.set(pitch=1.2, speed=1.2, rate=1)
        await player.set_filters(filters)
        await ctx.message.add_reaction("✅")

@bot.command()
async def slowed(ctx: commands.Context):
    """Applies a Slowed + Reverb effect."""
    player: wavelink.Player = ctx.voice_client
    if player:
        filters = player.filters
        filters.timescale.set(pitch=0.9, speed=0.8, rate=1)
        await player.set_filters(filters)
        await ctx.message.add_reaction("✅")

# ===== MISC COMMANDS =====
@bot.command()
async def loop(ctx: commands.Context):
    """Toggles looping the current song."""
    player: wavelink.Player = ctx.voice_client
    if not player:
        return

    if player.queue.mode == wavelink.QueueMode.normal:
        player.queue.mode = wavelink.QueueMode.loop
        await ctx.send(f"🔄 Looping **{player.current.title}**.")
    else:
        player.queue.mode = wavelink.QueueMode.normal
        await ctx.send(f"❌ Stopped looping **{player.current.title}**.")

@bot.command()
async def volume(ctx: commands.Context, value: int):
    """Changes the volume."""
    player: wavelink.Player = ctx.voice_client
    if not player:
        return await ctx.send("I'm not connected to a voice channel.")

    await player.set_volume(value)
    await ctx.send(f"🔊 Volume set to {value}%.")

@bot.command()
async def shuffle(ctx: commands.Context):
    """Shuffles the queue."""
    player: wavelink.Player = ctx.voice_client
    if not player:
        return

    player.queue.shuffle()
    await ctx.send("🔀 Queue shuffled.")

@bot.command()
async def clear(ctx: commands.Context):
    """Clears the queue."""
    player: wavelink.Player = ctx.voice_client
    if not player:
        return

    player.queue.clear()
    await ctx.send("🗑️ Cleared the queue.")

# Start the bot
async def main():
    async with bot:
        await bot.start(BOT_TOKEN)

asyncio.run(main())
