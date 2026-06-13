---
id: messaging-bots
title: Mesajlaşma Botları
sidebar_label: Mesajlaşma Botları
---

# Mesajlaşma Botları

`channels.<name>` altında bir kanal etkinleştirin ve token'larını sağlayın (genellikle
`${ENV_VAR}` aracılığıyla). Gateway yalnızca etkin kanalları başlatır ve eksik token'larda
çökmez — hatayı günlüğe kaydeder ve devam eder.

:::danger Ağ kanalları varsayılan olarak her göndereni reddeder
Telegram, Discord, Slack ve WhatsApp **varsayılan-rettir**: boş bir
`security.allowed_senders.<channel>` ile bir bot **her** göndereni — siz, yani
sahip dâhil — reddeder ve sahibe kimliğini hangi yapılandırma anahtarına ekleyeceğini
söyleyen sabit bir mesajla yanıt verir. Bu yüzden aşağıdaki her YAML bloğu eşleşen bir
`security.allowed_senders` girdisine ihtiyaç duyar, yoksa botla kimse konuşamaz.
Başlangıçta AETHON ayrıca, boş bir izin listesine sahip etkin her ağ botu için
`security.allowed_senders.<channel>`'ı adıyla anan gürültülü bir uyarı kaydeder.
`aethon init` sihirbazı bu kimlikleri toplar ve bu bölümü sizin için yazar; aşağıdakiler
gibi elle düzenlenmiş bir yapılandırmaya bunu kendiniz eklemelisiniz.
:::

## Telegram

Token almak için **BotFather** aracılığıyla bir bot oluşturun.

```yaml
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}

security:
  allowed_senders:
    telegram: ["123456789"]   # sayısal Telegram kullanıcı kimliğiniz — bu olmadan tüm gönderenler reddedilir
```

## Discord

**Discord Developer Portal**'da bir bot oluşturun ve ona **MESSAGE CONTENT** intent'ini
verin. Bot, DM'lere veya kendisini @bahseden mesajlara yanıt verir.

```yaml
channels:
  discord:
    enabled: true
    token: ${DISCORD_BOT_TOKEN}

security:
  allowed_senders:
    discord: ["your-discord-user-id"]   # bu olmadan tüm gönderenler reddedilir
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

security:
  allowed_senders:
    slack: ["U0123456789"]   # Slack kullanıcı kimliğiniz — bu olmadan tüm gönderenler reddedilir
```

## WhatsApp (deneysel)

Ek paketi kurun (`pip install "aethon-ai[whatsapp]"`), kanalı etkinleştirin ve ilk
başlangıçta oturumu bağlamak için **QR kodunu** WhatsApp uygulamanızla tarayın.

```yaml
channels:
  whatsapp:
    enabled: true

security:
  allowed_senders:
    whatsapp: ["1234567890"]   # numaranız (+ olmadan) — bu olmadan tüm gönderenler reddedilir
```

:::tip
Tüm kanallar arasında yalnızca **WhatsApp** ek bir kuruluma ihtiyaç duyar. CLI, WebChat, Telegram,
Discord ve Slack'in tümü çekirdek kurulumla birlikte gelir.
:::
