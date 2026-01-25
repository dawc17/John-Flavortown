from bot.bot import bot
from bot.config import TOKEN

import logging
import os

def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
       level=level,
       format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

if not TOKEN:
  raise RuntimeError("Bot token not set!")

configure_logging()

bot.run(TOKEN)