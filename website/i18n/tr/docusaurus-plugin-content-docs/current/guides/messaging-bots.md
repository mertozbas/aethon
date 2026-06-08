---
id: messaging-bots
title: Mesajlaşma Botları
sidebar_label: Mesajlaşma Botları
---

# Mesajlaşma Botları

`channels.<name>` altında bir kanal etkinleştirin ve token'larını sağlayın (genellikle
`${ENV_VAR}` aracılığıyla). Gateway yalnızca etkin kanalları başlatır ve eksik token'larda
çökmez — hatayı günlüğe kaydeder ve devam eder.

## Telegram

Token almak için **BotFather** aracılığıyla bir bot oluşturun.

```yaml
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}
```

## Discord

**Discord Developer Portal**'da bir bot oluşturun ve ona **MESSAGE CONTENT** intent'ini
verin. Bot, DM'lere veya kendisini @bahseden mesajlara yanıt verir.

```yaml
channels:
  discord:
    enabled: true
    token: ${DISCORD_BOT_TOKEN}
```

## Slack

Bir **Slack App** oluşturun, **Socket Mode**'u etkinleştirin ve
`message.channels`, `message.im`, `app_mention` olaylarına abone olun. Hem bir Bot Token'ına
hem de bir App-Level Token'ına ihtiyacınız vardır.

```yaml
channels:
  slack:
    enabled: true
    bot_token: ${SLACK_BOT_TOKEN}    # xoxb-…
    app_token: ${SLACK_APP_TOKEN}    # xapp-…
```

## WhatsApp (deneysel)

Ek paketi kurun (`pip install "aethon-ai[whatsapp]"`), kanalı etkinleştirin ve ilk
başlangıçta oturumu bağlamak için **QR kodunu** WhatsApp uygulamanızla tarayın.

```yaml
channels:
  whatsapp:
    enabled: true
```

:::tip
Tüm kanallar arasında yalnızca **WhatsApp** ek bir kuruluma ihtiyaç duyar. CLI, WebChat, Telegram,
Discord ve Slack'in tümü çekirdek kurulumla birlikte gelir.
:::
