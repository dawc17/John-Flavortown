# John Flavortown

A Discord bot for interacting with the Flavortown and Hackatime APIs. Allows users to search for projects, view shop items, track coding time, and compare stats with other users.

## Features

- **Search**: Find users or projects by name
- **List**: Browse shop items and projects with pagination
- **Stats**: View your Flavortown profile including cookies, devlog time, and projects
- **Time**: Display your coding time today from Hackatime
- **Overlap**: Compare your stats against a random user

## Security

API keys are encrypted with a user-provided password before storage. The bot operator cannot read plaintext keys. Keys are cached in memory for 2 hours after authentication to reduce password prompts.

## Installation

1. Clone the repository
2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Discord bot token:
   ```
   DISCORD_TOKEN=your_token_here
   GUILD_ID=your_guild_id  # Optional, for faster command sync
   ```
4. Run the bot:
   ```
   python -m bot.main
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/login` | Store your API key (Flavortown or Hackatime) |
| `/logout` | Remove stored API keys |
| `/status` | Check which services you are logged into |
| `/search` | Search for users or projects |
| `/list` | List shop items or projects |
| `/stats` | View your Flavortown stats |
| `/time` | View your Hackatime coding time today |
| `/overlap` | Compare your stats with a random user |

## Project Structure

```
bot/
    main.py          Entry point
    bot.py           Bot class and setup
    api.py           Flavortown API wrapper
    hackatime.py     Hackatime API wrapper
    storage.py       SQLite storage for encrypted keys
    crypto.py        Encryption utilities
    config.py        Environment configuration
    cogs/
        login.py     Authentication commands
        commands.py  Main commands (search, list, stats, time)
        overlap.py   User comparison command
        profile.py   Profile display
```

## Dependencies

- discord.py
- requests
- cryptography
- python-dotenv

## License

MIT