import discord
from discord.ext import commands
from bot.config import GUILD_ID

import logging
logger = logging.getLogger(__name__)

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
    await self.load_extension("bot.cogs.search")
    await self.load_extension("bot.cogs.devlogs")
    await self.load_extension("bot.cogs.projects")
    await self.load_extension("bot.cogs.system")
    if GUILD_ID: 
      guild = discord.Object(id=GUILD_ID)
      self.tree.copy_global_to(guild=guild)
      await self.tree.sync(guild=guild)
      logger.info("event=slash_sync scope=guild guild_id=%s", GUILD_ID)
    else:
      await self.tree.sync()
      logger.info("event=slash_sync scope=global")

  async def on_ready(self):
    logger.info("event=ready user=%s user_id=%s", self.user, self.user.id)
    logger.info("event=guild_count count=%s", len(self.guilds))
    print("------")

bot = JF()

@bot.command(name="sync")
@commands.is_owner() 
async def sync(ctx):
    bot.tree.copy_global_to(guild=ctx.guild)

    synced = await bot.tree.sync(guild=ctx.guild)
    
    await ctx.send(f"Synced {len(synced)} commands to this guild!")