---
id: messaging-bots
title: Messaging Bots
sidebar_label: Messaging Bots
---

# Messaging Bots

Enable a channel under `channels.<name>` and supply its token(s) (typically via
`${ENV_VAR}`). The gateway starts only enabled channels and won't crash on missing
tokens — it logs the error and keeps going.

:::danger Network channels deny every sender by default
Telegram, Discord, Slack, and WhatsApp are **default-deny**: a bot with an empty
`security.allowed_senders.<channel>` rejects **every** sender — including you, the
owner — and replies with a fixed message telling the owner which config key to add
their id to. Each YAML block below therefore needs a matching `security.allowed_senders`
entry, or nobody can talk to the bot. On startup AETHON also logs a loud warning naming
`security.allowed_senders.<channel>` for any enabled network bot with an empty allowlist.
The `aethon init` wizard collects these ids and writes this section for you; a hand-edited
config like the ones below must add it yourself.
:::

## Telegram

Create a bot via **BotFather** to get the token.

```yaml
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}

security:
  allowed_senders:
    telegram: ["123456789"]   # your numeric Telegram user id — without this, all senders are denied
```

## Discord

Create a bot in the **Discord Developer Portal** and grant it the **MESSAGE CONTENT**
intent. The bot responds to DMs or messages that @mention it.

```yaml
channels:
  discord:
    enabled: true
    token: ${DISCORD_BOT_TOKEN}

security:
  allowed_senders:
    discord: ["your-discord-user-id"]   # without this, all senders are denied
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

security:
  allowed_senders:
    slack: ["U0123456789"]   # your Slack user id — without this, all senders are denied
```

## WhatsApp (experimental)

Install the extra (`pip install "aethon-ai[whatsapp]"`), enable the channel, and on
first start scan the **QR code** with your WhatsApp app to link the session.

```yaml
channels:
  whatsapp:
    enabled: true

security:
  allowed_senders:
    whatsapp: ["1234567890"]   # your number (no +) — without this, all senders are denied
```

:::tip
Of all channels, only **WhatsApp** needs an extra install. CLI, WebChat, Telegram,
Discord, and Slack all ship in the core install.
:::
