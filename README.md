# John Flavortown

Discord bot for interacting with the Flavortown and Hackatime APIs. Provides commands to search users and projects, list shop items and projects, view profile stats, and fetch Hackatime time data.

## For users - invite link
https://discord.com/oauth2/authorize?client_id=1463103382104440946&permissions=277025442816&integration_type=0&scope=applications.commands+bot

## Features

- Search users or projects
- List shop items and projects with pagination
- Show Flavortown profile details
- Show Hackatime coding time today
- Compare your stats with a random Flavortown user

## Security

API keys are encrypted with a user provided password before storage. The bot operator cannot read plaintext keys. Keys are cached in memory for a limited time to reduce password prompts.

## Requirements

- Python 3.8 or newer
- Discord bot token
- Flavortown API key and Hackatime API key for users

## Installation

1. Clone the repository.
2. Create a virtual environment and install dependencies.

   Windows:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

   Linux or macOS:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

3. Create a .env file in the project root.

   DISCORD_TOKEN=your_token_here
   GUILD_ID=your_guild_id
   LOG_LEVEL=INFO
   PAGINATION_VIEW_TIMEOUT_SECONDS=180
   SHOP_PAGE_SIZE=10
   PROJECT_PAGE_SIZE=20
   SEARCH_USERS_PAGE_SIZE=25
   SEARCH_PROJECTS_PAGE_SIZE=20

4. Run the bot.

   python -m bot.main

## Configuration

Environment variables:

- DISCORD_TOKEN. Required.
- GUILD_ID. Optional. If set, commands are synced to that guild for faster updates.
- LOG_LEVEL. Optional. Defaults to INFO.
- PAGINATION_VIEW_TIMEOUT_SECONDS. Optional. Defaults to 180.
- SHOP_PAGE_SIZE. Optional. Defaults to 10.
- PROJECT_PAGE_SIZE. Optional. Defaults to 20.
- SEARCH_USERS_PAGE_SIZE. Optional. Defaults to 25.
- SEARCH_PROJECTS_PAGE_SIZE. Optional. Defaults to 20.
- FLAVORTOWN_SERVICE_API_KEY. Optional. Used for devlog polling notifications.
- DEVLOG_POLL_INTERVAL_SECONDS. Optional. Defaults to 600.
- ADMIN_USER_IDS. Optional. Comma-separated Discord user IDs with admin access.
- DEFAULT_TIMEZONE. Optional. Defaults to UTC.
- DEFAULT_PUBLIC_OUTPUT. Optional. Defaults to false.
- DEFAULT_SERVICE. Optional. Defaults to flavortown.

## Commands

| Command          | Description                                    |
| ---------------- | ---------------------------------------------- |
| /login           | Store your API key for Flavortown or Hackatime |
| /logout          | Remove stored API keys                         |
| /status          | Check which services you are logged into       |
| /search          | Search for users or projects                   |
| /list            | List shop items or projects                    |
| /profile         | Show Flavortown profile                        |
| /time            | Show Hackatime coding time today               |
| /overlap         | Compare stats with a random user               |
| /health          | Show bot health information                    |
| /project-create  | Create a project                               |
| /project-update  | Update a project                               |
| /project-mine    | List your projects                             |
| /devlog-create   | Create a devlog entry                          |
| /devlog-list     | List recent devlogs                            |
| /devlog-view     | View a devlog by ID                            |
| /project-devlogs | List devlogs for a project                     |

## Data Storage

- SQLite database stored at data/keys.db
- Encrypted API keys with per user per service rows

## Testing

Activate the virtual environment and run tests:

pytest

## Deployment

1. Copy .env.example to .env and fill in required values.
2. Build and run with Docker Compose.

   docker compose up -d --build

The compose file mounts data/ for persistence and loads environment variables from .env.

To stop:

docker compose down

## Project Files

Key files:

- bot/main.py entry point
- bot/bot.py bot setup and startup
- bot/api.py Flavortown API wrapper
- bot/hackatime.py Hackatime API wrapper
- bot/http.py shared request helpers
- bot/storage.py SQLite storage
- bot/crypto.py encryption utilities
- bot/config.py environment configuration
- bot/utils.py shared helpers
- bot/cogs/login.py authentication commands
- bot/cogs/views.py pagination and confirmation views
- bot/cogs/search.py search and list commands
- bot/cogs/devlogs.py devlog commands
- bot/cogs/projects.py project commands
- bot/cogs/system.py health and time commands
- bot/cogs/overlap.py comparison command
- bot/cogs/profile.py profile command

## License

MIT
