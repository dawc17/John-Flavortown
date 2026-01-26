# Discord Bot Setup (Your Own Application)

This guide walks you through creating a Discord application and configuring it to run this bot.

## 1) Create the application

1. Go to the Discord Developer Portal: https://discord.com/developers/applications
2. Click **New Application**, name it, and create it.

## 2) Create a bot user

1. In your application, open **Bot** in the left sidebar.
2. Click **Add Bot**.
3. (Optional) Toggle **Public Bot** off if you want only you to invite it.
4. Under **Privileged Gateway Intents**, enable the intents the bot requires (common ones are **Server Members** and **Message Content**).

## 3) Get the bot token

1. On the **Bot** page, click **Reset Token** and copy the token.
2. Store it safely. Anyone with this token can control the bot.

## 4) Set up environment variables

This project reads configuration from environment variables (typically from a `.env` file).

1. Create or update your `.env` file at the project root.
2. Add your bot token and any other required config values.

Typical example:

```
DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
```

If the project expects additional variables, check the project README or configuration module in the bot code and mirror them here.

## 5) Invite the bot to your server

1. Go to **OAuth2** → **URL Generator**.
2. Under **Scopes**, select **bot** (and **applications.commands** if you need slash commands).
3. Under **Bot Permissions**, select the permissions the bot needs.
4. Copy the generated URL, open it in your browser, and choose a server where you have permission to invite bots.

## 6) Run the bot

Start the bot using your normal project run method (see the project README for the exact command).

## Troubleshooting

- **401 Unauthorized / Invalid token**: Regenerate the token and update `.env`.
- **Missing message content**: Enable **Message Content Intent** under **Privileged Gateway Intents**.
- **Bot not responding**: Confirm it is online, invited to the server, and has the right permissions.
