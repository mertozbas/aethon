---
id: messaging-bots
title: Messaging Bots
sidebar_label: Messaging Bots
---

# Messaging Bots

Enable a channel under `channels.<name>` and supply its token(s) (typically via
`${ENV_VAR}`). The gateway starts only enabled channels and won't crash on missing
tokens — it logs the error and keeps going.

## Telegram

Create a bot via **BotFather** to get the token.

```yaml
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}
```

## Discord

Create a bot in the **Discord Developer Portal** and grant it the **MESSAGE CONTENT**
intent. The bot responds to DMs or messages that @mention it.

```yaml
channels:
  discord:
    enabled: true
    token: ${DISCORD_BOT_TOKEN}
```

## Slack

Create a **Slack App**, enable **Socket Mode**, and subscribe to events
`message.channels`, `message.im`, `app_mention`. You need both a Bot Token and an
App-Level Token.

```yaml
channels:
  slack:
    enabled: true
    bot_token: ${SLACK_BOT_TOKEN}    # xoxb-…
    app_token: ${SLACK_APP_TOKEN}    # xapp-…
```

## WhatsApp (experimental)

Install the extra (`pip install "aethon-ai[whatsapp]"`), enable the channel, and on
first start scan the **QR code** with your WhatsApp app to link the session.

```yaml
channels:
  whatsapp:
    enabled: true
```

:::tip
Of all channels, only **WhatsApp** needs an extra install. CLI, WebChat, Telegram,
Discord, and Slack all ship in the core install.
:::
