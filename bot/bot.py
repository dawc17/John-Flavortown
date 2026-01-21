import discord
from discord.ext import commands
from bot.config import GUILD_ID

intents = discord.Intents.default()

class JF(commands.Bot):
  def __init__(self):
    super().__init__(
      command_prefix="!",
      intents=intents,
      application_id=None
    )

  async def setup_hook(self) -> None:
    await self.load_extension("bot.cogs.login")
    await self.load_extension("bot.cogs.profile")
    await self.load_extension("bot.cogs.overlap")
    await self.load_extension("bot.cogs.commands")
    if GUILD_ID: 
      guild = discord.Object(id=GUILD_ID)
      self.tree.copy_global_to(guild=guild)
      await self.tree.sync(guild=guild)
      print(f"Slash commands synced to guild {GUILD_ID}")
    else:
      await self.tree.sync()
      print("Global slash commands synced (may take up to 1 hour)")

  async def on_ready(self):
    print(f"Logged in as {self.user} (ID: {self.user.id})")
    print(f"Connected to {len(self.guilds)} guild(s)")
    print("------")

bot = JF()

@bot.command(name="sync")
@commands.is_owner() 
async def sync(ctx):
    bot.tree.copy_global_to(guild=ctx.guild)

    synced = await bot.tree.sync(guild=ctx.guild)
    
    await ctx.send(f"Synced {len(synced)} commands to this guild!")