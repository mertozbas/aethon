# Backup, Restore & Run-at-Boot

AETHON keeps all of its state under `~/.aethon` (config, sessions, memory,
recordings, scheduled jobs). This page covers backing it up and running AETHON
automatically at login.

## Backup

```bash
aethon backup                 # → ~/.aethon-backup-<timestamp>.tar.gz
aethon backup -o /path/out.tar.gz
```

`aethon backup` archives `~/.aethon` to a `.tar.gz`. SQLite databases
(`memory.sqlite`) are copied with the live-safe backup API, so the archive is
**consistent even while the gateway is running**; the transient `logs/` folder
is skipped.

For a fully-quiescent backup you can also just stop AETHON and tar the directory
yourself:

```bash
tar -czf aethon-backup.tar.gz -C ~ .aethon          # while stopped
sqlite3 ~/.aethon/memory.sqlite ".backup mem.bak"   # live DB snapshot
```

**Docker:** the state lives in the `aethon-data` named volume — back it up with

```bash
docker run --rm -v aethon-data:/data -v "$PWD":/out alpine \
  tar -czf /out/aethon-data.tar.gz -C /data .
```

## Restore

```bash
# stop AETHON first
tar -xzf ~/.aethon-backup-<timestamp>.tar.gz -C ~/.aethon
```

(The archive paths are relative to `~/.aethon`.) For Docker, extract into the
volume the same way you backed it up.

## Run at boot

```bash
aethon service install
```

This writes a service unit that keeps `aethon start` running and restarts it on
failure, with stdout/err in `~/.aethon/logs/`:

- **macOS:** a launchd agent at `~/Library/LaunchAgents/com.aethon.gateway.plist`.
  Enable it with `launchctl load <path>`.
- **Linux:** a systemd **user** unit at `~/.config/systemd/user/aethon.service`.
  Enable it with `systemctl --user daemon-reload && systemctl --user enable --now aethon`.

The command prints the exact enable command for your platform. Retention (old
session-reset backups and recordings) is pruned automatically at each boot — see
the `retention` config.
