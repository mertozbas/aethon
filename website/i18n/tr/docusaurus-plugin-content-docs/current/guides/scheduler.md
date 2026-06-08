---
id: scheduler
title: Zamanlayıcı (cron işleri)
sidebar_label: Zamanlayıcı
---

# Zamanlayıcı (cron işleri)

Zamanlayıcı (APScheduler), bir SOP çalıştıran ve sonucu bir kanala teslim eden cron işleri
yürütür (`scheduler.default_channel` değerinden gelen varsayılan kanal, ki bu `cli`'dir). 
SOP'ların etkin olmasını gerektirir (`sops.enabled: true`, varsayılan). İşleri yapılandırmada tanımlayın:

```yaml
scheduler:
  enabled: true
  default_channel: cli
  jobs:
    weekday-standup:
      cron: "0 9 * * 1-5"        # weekdays at 9 AM
      sop_name: codebase-summary
      channel: telegram          # optional; overrides default_channel
      recipient: "123456789"     # the destination chat/channel id (see note)
```

:::note Alıcılar
`cli` ve `webchat` için `recipient` gerekmez. Mesajlaşma kanalları için (`telegram`,
`discord`, `slack`, `whatsapp`), `recipient` değerini hedef sohbet/kanal id'sine ayarlayın —
aksi takdirde teslimat bir uyarı ile atlanır.
:::

## İşleri çalışma zamanında yönetme

Asistan, çalışırken işleri `schedule_task`, `list_scheduled_jobs` ve `remove_scheduled_job`
araçlarıyla da yönetebilir — bkz. **[Araçlar](../concepts/tools.md)**.
