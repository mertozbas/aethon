---
id: scheduler
title: Scheduler (cron jobs)
sidebar_label: Scheduler
---

# Scheduler (cron jobs)

The scheduler (APScheduler) runs cron jobs that execute an SOP and deliver the result
to a channel (default channel from `scheduler.default_channel`, which is `cli`). It
requires SOPs to be enabled (`sops.enabled: true`, the default). Define jobs in config:

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

:::note Recipients
`cli` and `webchat` need no `recipient`. For messaging channels (`telegram`,
`discord`, `slack`, `whatsapp`), set `recipient` to the destination chat/channel id —
otherwise delivery is skipped with a warning.
:::

## Managing jobs at runtime

The assistant can also manage jobs while running with the `schedule_task`,
`list_scheduled_jobs`, and `remove_scheduled_job` tools — see
**[Tools](../concepts/tools.md)**.
