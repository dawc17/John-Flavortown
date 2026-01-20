from bot.bot import bot
from bot.config import TOKEN

if not TOKEN:
  raise RuntimeError("Bot token not set!")

bot.run(TOKEN)