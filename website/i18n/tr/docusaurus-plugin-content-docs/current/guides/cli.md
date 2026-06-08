---
id: cli
title: Etkileşimli CLI
sidebar_label: Etkileşimli CLI
---

# Etkileşimli CLI

`aethon start` komutunu çalıştırdığınızda konsol bir durum bloğu yazdırır: sağlayıcı ve
model, WebChat URL'si (`http://127.0.0.1:18790`), bellek/çoklu-ajan/SOP/
zamanlayıcı/telemetri durumu ve (etkinleştirildiğinde) dashboard ve webhook URL'leri ile
etkin kanalların listesi. Ardından gateway başlar.

CLI kanalı varsayılan olarak etkindir. `aethon start` sonrasında `you > `
isteminde yazın. Yanıtlar Markdown olarak işlenir. Girdi geçmişi `~/.aethon/cli_history`
dosyasına kaydedilir. `exit`, `quit`, `q` veya Ctrl-C / EOF ile çıkış yapın.

```
you > what's on my plate today?
you > /code-assist refactor the auth module
you > exit
```

`/` ile başlayan bir mesaj bir **SOP** komutu olarak ele alınır — bkz.
**[SOP'lar](../concepts/sops.md)**. Diğer her şey, orkestratör ajanı tarafından işlenen
normal bir sohbet adımıdır (uzmanlara devredebilir veya araç çağırabilir).
