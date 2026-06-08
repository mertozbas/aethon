---
id: configuration
title: Yapılandırma
sidebar_label: Yapılandırma
---

# Yapılandırma

- **Dosya konumu:** `~/.aethon/config.yaml` (herhangi bir komutta `--config / -c` ile değiştirilebilir).
- **Biçim:** YAML, Pydantic ile doğrulanır. **Eksik veya boş bir dosya, tamamen varsayılan değerlere sahip bir yapılandırma üretir** — her bölüm kendi varsayılanlarına geri döner.
- **Yazma:** sihirbaz ve araçlar, YAML'ı `sort_keys=False` ve `allow_unicode=True` ile yazar; gerektiğinde üst dizinleri oluşturur.

:::tip
Bu sayfa kavramsal rehberdir. Her yapılandırma bölümünün alan alan eksiksiz bir
tablosu için **[Yapılandırma Başvurusu](../reference/configuration.md)** sayfasına bakın.
:::

## Sihirbaza bırakın

Çoğu kişi dosyayı asla elle düzenlemez. Çalıştırın:

```bash
aethon init     # ~/.aethon/config.yaml yazar
aethon doctor   # sağlayıcıyı/modeli + belleği doğrular
```

`aethon init` bir sağlayıcı menüsünde (**openai / anthropic / ollama**) ilerler,
mesajlaşma botlarını yapılandırır ve (Ollama gömmeleri için) Ollama'yı kurmayı ve
gömme modelini indirmeyi önerir. Bir yol seçmek için `--config / -c`, mevcut bir
yapılandırmayı sormadan üzerine yazmak için `--force` kullanın.

## `${ENV_VAR}` çözümlemesi

Bir string değeri, **yalnızca `${` ile başlayıp `}` ile bitiyorsa** bir ortam
değişkeni referansı olarak ele alınır (yalnızca tam string — kısmi veya araya
yerleştirilmiş yer değiştirme yoktur). İçteki ad `os.environ` üzerinden aranır.
**Eksik bir ortam değişkeni, bir hataya değil boş bir string `""` değerine
çözümlenir.** Çözümleme dict'lere ve list'lere özyinelemeli olarak iner; int, bool,
float ve `None` değişmeden geçer.

```yaml
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}   # gerçek gizli değer ortam üzerinden sağlanır
```

:::note
Gizli değerleri yapılandırmaya işlemek (commit etmek) yerine `~/.aethon/credentials/telegram.env`
gibi dosyalarda tutun ve onları ortama dışa aktarın (export edin).
:::

## Minimal bir yapılandırma

İşe yarayan en küçük yapılandırma yalnızca bir sağlayıcı ve bir anahtar seçer:

```yaml
model:
  provider: openai
  model_id: gpt-4o
  api_key: ${OPENAI_API_KEY}
```

Diğer her şey (kanallar, bellek, çok ajanlılık, SOP'ler, zamanlayıcı, pano,
webhook, telemetri…) makul varsayılanlara geri döner. İhtiyacınız oldukça
özellikleri açın — bölümlerin ve varsayılanların tam seti için
**[Yapılandırma Başvurusu](../reference/configuration.md)** sayfasına bakın.

## Yetenekler ve çalışma zamanı özellikleri (tercihe bağlı)

Daha yeni yetenek blokları, aksi belirtilmedikçe **varsayılan olarak kapalıdır**.
Güçlü veya ana makineyi etkileyen özellikler, siz tercih edene kadar devre dışı
kalır ve geri kalanı güvenlik ve onay kancaları kapılar. (Canlı durumu panonun
**Özellikler** panelinden inceleyebilirsiniz.)

```yaml
# Pakete dahil edilen yardımcı araçlar (scraper/github/jsonrpc/notify varsayılan AÇIK; computer KAPALI).
capabilities:
  scraper:  { enabled: true }
  github:   { enabled: true }      # use_github ($GITHUB_TOKEN okur)
  jsonrpc:  { enabled: true }
  notify:   { enabled: true, method: auto }
  computer: { enabled: false, require_approval: true }   # ⚠ ekran/fare/klavye; [computer] + macOS izinleri gerektirir

# macOS yerel araçları (yalnızca Darwin). Messages ve Keychain açıkça tercihe bağlıdır.
macos:
  enabled: true
  enable_calendar: true
  enable_reminders: true
  enable_mail: true
  enable_notes: true
  enable_shortcuts: true
  enable_messages: false           # ⚠ sizin adınıza iMessage/SMS gönderebilir
  enable_keychain: false           # ⚠ Keychain'i okuyabilir/yazabilir
  actions_requiring_approval: ["mail.send", "messages.send", "keychain.set"]

lsp:                               # [lsp] (pyright) / PATH'te dil sunucuları gerektirir
  enabled: false
  auto_diagnostics: false          # dosya değiştiren araçlardan sonra tanılamayı ekle

runtime_tools:                     # manage_tools (sandbox'lanmış dinamik araç yükleme)
  enabled: false
  allow_create: false              # create/fetch (alt süreç sandbox'ı önce doğrular)
  allow_install: false             # add/reload (eksik paketleri otomatik kurar)

session_recorder:                  # zaman çizelgesi + anlık görüntüler → ZIP, panoda tekrar
  enabled: false
  max_events: 10000

ambient:                           # proaktif / otonom boş zaman çalışması
  enabled: false
  auto_start: false

prompt:                            # sistem istemi farkındalık katmanları
  include_environment: true
  include_learnings: true
  include_recent_logs: true
  include_shell_history: false     # gizlilik
  include_self_awareness: false    # ana kaynak dosyalarını gömer — ağır

performance:
  max_tool_output_chars: 12000     # tek bir araç sonucunu sınırla ki bağlamı taşıramasın (0 = kapalı)

paths:
  recordings: "~/.aethon/recordings"
```

Bunların her birinin neyi açtığını öğrenmek için **[Yetenekler](../concepts/capabilities.md)** sayfasına bakın.
