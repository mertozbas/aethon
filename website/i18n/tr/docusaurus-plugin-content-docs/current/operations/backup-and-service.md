---
id: backup-and-service
title: Yedekleme, Geri Yükleme ve Açılışta Çalıştırma
sidebar_label: Yedekleme ve Hizmet
---

# Yedekleme, Geri Yükleme ve Açılışta Çalıştırma

AETHON, tüm durumunu `~/.aethon` altında tutar (yapılandırma, oturumlar, bellek,
kayıtlar, zamanlanmış işler). Bu sayfa, bunun yedeklenmesini ve AETHON'un oturum
açılışında otomatik olarak çalıştırılmasını ele alır.

## Yedekleme

```bash
aethon backup                 # → ~/.aethon-backup-<timestamp>.tar.gz
aethon backup -o /path/out.tar.gz
```

`aethon backup`, `~/.aethon` dizinini bir `.tar.gz` dosyasına arşivler. SQLite
veritabanları (`memory.sqlite`), canlı-güvenli yedekleme API'siyle kopyalanır;
böylece arşiv, **gateway çalışırken bile tutarlıdır**; geçici `logs/` klasörü atlanır.

Tümüyle hareketsiz (quiescent) bir yedek için, AETHON'u durdurup dizini kendiniz de
tar'layabilirsiniz:

```bash
tar -czf aethon-backup.tar.gz -C ~ .aethon          # durdurulmuşken
sqlite3 ~/.aethon/memory.sqlite ".backup mem.bak"   # canlı DB anlık görüntüsü
```

**Docker:** durum, `aethon-data` adlı volume içinde yaşar — şununla yedekleyin:

```bash
docker run --rm -v aethon-data:/data -v "$PWD":/out alpine \
  tar -czf /out/aethon-data.tar.gz -C /data .
```

## Geri Yükleme

```bash
# önce AETHON'u durdurun
tar -xzf ~/.aethon-backup-<timestamp>.tar.gz -C ~/.aethon
```

(Arşiv yolları `~/.aethon` dizinine görelidir.) Docker için, yedeklediğiniz yöntemle
aynı şekilde volume'ün içine çıkarın.

## Açılışta çalıştırma

```bash
aethon service install
```

Bu komut, `aethon start`'ı çalışır durumda tutan ve başarısızlıkta yeniden başlatan,
stdout/err çıktıları `~/.aethon/logs/` içinde olan bir hizmet birimi yazar:

- **macOS:** `~/Library/LaunchAgents/com.aethon.gateway.plist` konumunda bir launchd
  ajanı. `launchctl load <path>` ile etkinleştirin.
- **Linux:** `~/.config/systemd/user/aethon.service` konumunda bir systemd **kullanıcı**
  birimi. `systemctl --user daemon-reload && systemctl --user enable --now aethon` ile
  etkinleştirin.

Komut, platformunuz için tam etkinleştirme komutunu yazdırır. Saklama (retention) —
eski oturum-sıfırlama yedekleri ve kayıtlar — her açılışta otomatik olarak budanır;
`retention` yapılandırmasına bakın.
