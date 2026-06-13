---
id: token-economy
title: Token ekonomisi
sidebar_label: Token ekonomisi
---

# Token ekonomisi

Sürekli çalışan, kendi kendine barındırılan bir asistan sessizce token yakabilir.
AETHON'un token ekonomisi alt sistemi, bilinçli kaldıraçlardan oluşan bir kümedir —
harcamayı ölçün, eski bağlamı sıkıştırın, yeniden okumadan yönelin, hacimli okumaları
yalıtın ve istem önbelleğini sıcak tutun. Belirtilmediği sürece her kaldıraç **isteğe
bağlı / varsayılan kapalıdır**.

## Bütçe ölçümü + günlük tavan (`budget`)

Token kullanımı tur başına ölçülür. `budget.daily_usd` değeri `0`'ın üzerine
ayarlandığında, harcama tavana yaklaştıkça turlar uyarılır (`budget.warn_ratio`,
varsayılan `0.8`) ve tavan aşıldığında **engellenir** — aynı yoldan geçen ortam ve
zamanlayıcı turları dâhil. `budget.pricing`, yerleşik fiyat tablosunu (1M token başına USD)
geçersiz kılar. Bu, "bir API yüzlerce dolar yakacak" korkusunun gerçek panzehridir.

```yaml
budget:
  daily_usd: 0.0        # 0 = sınırsız (yalnızca ölç)
  warn_ratio: 0.8       # harcama tavanın bu oranını aştığında bir kez uyar
  pricing: {}           # {model_substring: {input: x, output: y}} 1M token başına
```

## Geçmiş sıkıştırma (`session.compact_*`)

Uzun ufuklu bir oturumda, modelin girdisindeki eski, büyük araç çıktıları birikir.
`session.compact_enabled` açıkken (varsayılan **kapalı**), eski, büyük araç sonuçları
özlü bir işaretleyiciyle değiştirilir; böylece konuşma uygun maliyetli kalır. **Yığınlar
hâlinde** sıkıştırır — ve en son turlara asla dokunmaz — bu nedenle sağlayıcı mesaj
önbelleğini her turda değil, nadiren bozar.

```yaml
session:
  compact_enabled: false
  compact_keep_last_n_turns: 4    # en son N tura asla dokunma
  compact_min_chars: 800          # yalnızca bundan büyük bir sonucu sıkıştır
  compact_trigger_chars: 16000    # bu kadar eski yığın birikince bir geçiş çalıştır
```

## Repo haritası (`repo_map.enabled`)

Açıkken (varsayılan **kapalı**), ajanın okuduğu dosyalar özetlenir — yol → amaç, semboller,
içerik özeti (hash) — `workspace/REPO_MAP.json` içinde ve bir `## Repo Map` istem katmanı
olarak özlü bir harita enjekte edilir. Böylece bir sonraki oturum, aynı dosyaları yeniden
okumadan yönelir. Harita üst sınıra çekilir (en yeni `max_files`, `max_file_bytes`
altındaki dosyalar ve bir `max_snapshot_chars` istem katmanı boyut sınırı) ve katman
önbellek güvenlidir.

```yaml
repo_map:
  enabled: false
  max_files: 100
  max_file_bytes: 200000
  max_snapshot_chars: 2000
```

## Scout — çok oku, az döndür (`ask_scout`)

Scout uzman, gösterdiğiniz kaynakları okur/arar ve **yalnızca** özlü bir sonuç döndürmesi
talimatını alır. Ham malzeme, ana ajanın değil scout'un bağlamında kalır — böylece "bu
dosyaları oku ve bana X'i söyle" dosyaları turunuza dökmez. (Yalıtım tavsiye
niteliğindedir — scout'un kendi görev tanımına uymasına dayanır, araç çıktısı üst sınırı
yapısal güvence olarak kalır.) Bkz. **[Çok ajanlı uzmanlar](./multi-agent.md)**.

## Yetenek diyeti (`core_loop.capability_diet`)

Ağır, alana özgü araçlar, her turda yanlarında taşınan büyük şemalar taşır. Diyet, her
zaman açık olan bir çekirdek araç setini tutar ve ağır araçları (`use_mac`, `use_computer`,
`use_github`, `apple_notes`, `scraper`, `jsonrpc`) bir oturuma yalnızca o oturumun kurucu
mesajı bunların anahtar sözcükleriyle eşleştiğinde yükler — tur başına değil, oturum başına
bir kez kararlaştırılır; böylece istem/araç önbelleği sıcak kalır. Varsayılan olarak kapalı.
Bkz. **[Yetenekler](./capabilities.md)**.

## İstem önbelleği katmanlaması

Sistem istemi, **kararlı bir önek** artı **değişken bir kuyruk** olarak inşa edilir. Tur
başına değişen içerik (mevcut bağlam, hatırlanan bellekler, açık görevler anlık görüntüsü,
zaman damgası) kuyrukta yaşar; böylece değişmeyen bir tur yalnızca kuyruğu yeniden gönderir
ve önbelleğe alınmış öneki sıcak tutar. Değişken katmanlar yalnızca kaynakları gerçekten
değiştiğinde yenilenir ve tur başına günlük kuyruğu, her turu benzersiz kılıp önbelleğe
almayı boşa çıkarmasın diye kasıtlı olarak istemin dışında tutulur.
