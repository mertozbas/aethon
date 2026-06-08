---
id: capabilities
title: Yetenekler (0.2.0)
sidebar_label: Yetenekler
---

# Yetenekler (0.2.0)

0.2.0'da eklenen yetenekler için bir başvuru. Buradaki her şey **yapılandırmayla kapı
tutulur**; güçlü/ana makineyi etkileyen özellikler varsayılan olarak **kapalıdır** ve
güvenlik ile onay hook'ları üzerinden yönlendirilir. Canlı durumu panonun **Features**
panelinde inceleyin.

:::info Tasarım ilkesi
Yetenekler, mevcut çalışma zamanına standart araç/hook genişletme noktaları aracılığıyla
takılır; hiçbir şey güvenlik veya onay kapılarını atlamaz ve ağır/isteğe bağlı
bağımlılıklar `pip` ekleri olarak yalıtılır.
:::

## Yetenek araçları (`capabilities` bloğu)

| Araç | Ne yapar | Etkinleştirme | Notlar |
|---|---|---|---|
| `scraper` | BeautifulSoup HTML/XML kazıma ve ayrıştırma | `capabilities.scraper.enabled` (açık) | ek: `scraper` (beautifulsoup4) |
| `use_github` | GitHub GraphQL sorguları + mutasyonları | `capabilities.github.enabled` (açık) | `$GITHUB_TOKEN` değerini okur; mutasyonlar onay farkındalıklıdır |
| `jsonrpc` | HTTP/WebSocket üzerinden JSON-RPC | `capabilities.jsonrpc.enabled` (açık) | kimlik doğrulama günlüklerde gizlenir |
| `notify` | Yerel macOS bildirimi / zil / konuşma | `capabilities.notify.enabled` (açık) | varsayılan `method: auto` |
| `use_computer` | Ekran / fare / klavye otomasyonu | `capabilities.computer.enabled` (**kapalı**) | ⚠ yüksek riskli; ek `computer` (pyautogui); macOS Erişilebilirlik izni; onay kapılı |
| `manage_messages` | Ajanın kendi konuşmasının tur farkındalıklı incelemesi | her zaman açık | salt okunur |

Güvenlik hook'u scraper URL'lerini günlüğe kaydeder ve GitHub belirtecini / JSON-RPC
kimlik doğrulamasını gizler.

## macOS yerel (`macos` bloğu, yalnızca Darwin)

`use_mac` (Calendar, Reminders, Mail, Contacts, Safari, Finder, System Events,
Shortcuts, Messages, Music, Keychain, ham AppleScript/JXA) ve `apple_notes`
(listeleme/görüntüleme/arama/dışa aktarma + oluşturma/düzenleme/ekleme/silme/taşıma).

- Yalnızca macOS'ta **ve** `macos.enabled` etkinken kaydedilir.
- **Messages ve Keychain varsayılan olarak kapalıdır** (`enable_messages`,
  `enable_keychain`); güvenlik hook'u devre dışıyken bu eylem gruplarını kesin olarak
  engeller.
- Onay hook'u `macos.actions_requiring_approval` değerini kapı altında tutar (varsayılan
  `mail.send`, `messages.send`, `keychain.set`); keychain parolaları günlüklerden
  gizlenir.
- `macos` eki, `apple_notes` için daha zengin Markdown ekler (onsuz da düzgünce çalışır).

## Kod zekası — LSP (`lsp` bloğu)

`lsp`; dil sunucuları (talep üzerine başlatılan pyright/typescript-language-server/gopls/
rust-analyzer/clangd) aracılığıyla tanılama, tanıma gitme, başvuruları bulma, üzerine
gelme (hover) ve belge sembolleri sağlar. Önyüklemede sunucu başlatmamak için varsayılan
olarak kapalıdır.

- `lsp.enabled` aracı kaydeder; `lsp.auto_diagnostics`, dosya değiştiren araçlardan sonra
  tanılamalar ekler (ev dizini kapsamlı, üst sınırlı).
- `lsp` eki pyright'ı kurar; diğer dil sunucularını PATH üzerinde kendiniz kurun.

## Dinamik araç yükleme — `manage_tools` (`runtime_tools` bloğu)

Çalışma zamanında araç oluşturma/getirme/ekleme/yeniden yükleme/kaldırma; yüklenmeden
önce bir **alt süreç yalıtım ortamında (subprocess sandbox)** doğrulanır. Varsayılan
olarak kapalı. Üç kapı katmanı:

1. `runtime_tools.enabled` kaydı tamamen kapı altında tutar.
2. Güvenlik hook'u, `allow_create` olmadıkça `create`/`fetch` eylemlerini ve
   `allow_install` olmadıkça `add`/`reload` eylemlerini engeller.
3. Araç içi bir denetim (enjekte edilen yapılandırmayı okuyarak) devre dışı bırakıldığında
   tehlikeli eylemleri reddeder. Salt okunur eylemler (`list`/`discover`/`sandbox`) her
   zaman izinlidir; onay hook'u yalnızca kod yükleyen eylemler için sorar.

## Ortam / özerk mod (`ambient` bloğu)

Proaktif (boşta tetiklenen) veya özerk (sürekli) iş yapan bir arka plan döngüsü.
**Varsayılan olarak uykuda** — `ambient.enabled=false` ile hiçbir araç kaydedilmez ve
hiçbir görev çalışmaz. Çalışma zamanı anahtarı `start_ambient_mode` / `stop_ambient_mode`
/ `get_ambient_status`'tur. Yinelemeler ayrılmış bir oturumda çalışır (canlı sohbetlerle
çakışma yok), bir iş parçacığı yürütücüsüne aktarılır (mesaj açlığı yok) ve sunucu
tarafındaki bir tamamlanma sinyali özerk çalıştırmaları durdurur. `auto_start` varsayılan
olarak kapalıdır.

## Oturum kaydı ve yeniden oynatma (`session_recorder` bloğu)

Oturum zaman çizelgesini (araç çağrıları/sonuçları, model çağrıları) ve her turdan sonra
durum anlık görüntülerini kaydeder; kapanışta bir ZIP'e dışa aktarır. Varsayılan olarak
kapalı. Panonun **Recordings** sekmesinden inceleyin ve devam ettirin (listeleme /
olaylar / anlık görüntüler / yeniden oynatma önizlemesi). Yeniden oynatma önizlemesi
asla canlı ajanı veya sunucunun çalışma dizinini değiştirmez.

## MCP sunucusu — `aethon mcp`

`aethon mcp`, AETHON'un tüm araç setini MCP istemcilerine (ör. Claude Desktop) stdio
üzerinden sunar. Araçlar hook zinciri aracılığıyla çağrılır (güvenlik uygulanır); onay
gerektiren araçlar reddedilir (stdio üzerinde etkileşimli kanal yok); araç stdout'u, JSON-RPC
akışını bozamayacak şekilde başka yöne yönlendirilir. `runtime.get_tools_schemas()`
şemaları duyurur.

## Sistem istemi farkındalığı (`prompt` bloğu)

Sistem istemine katlanan, isteğe bağlı ve tek tek kapı tutulan katmanlar:

- `include_environment` (açık) — OS/mimari/Python/cwd/ev/kabuk/ana makine.
- `include_learnings` (açık) — `record_learning` aracı tarafından yazılan `LEARNINGS.md`.
- `include_recent_logs` (açık) — `<paths.logs>/aethon.log` dosyasının sonu (bir döner dosya işleyicisi besler).
- `include_shell_history` (**kapalı**, gizlilik) — son bash/zsh geçmişi.
- `include_self_awareness` (**kapalı**) — anahtar kaynak dosyaları gömer (ağır; turları yavaşlatır).

## Bağlam taşması koruması (`performance.max_tool_output_chars`)

Binlerce satır döken bir araç (ruff, mypy, büyük grep'ler) aksi takdirde modelin
bağlamını taşırırdı. Aşırı büyük araç çıktısı, modele ulaşmadan önce üst sınıra çekilir
(varsayılan ~12000 karakter, baş + son + bir kırpma işareti). Devre dışı bırakmak için
`0` olarak ayarlayın.

## macOS menü çubuğu başlatıcısı (`launcher-macos` eki)

`aethon-menubar`, `launcher-macos` ekiyle kurulan isteğe bağlı bir `rumps` menü çubuğu
uygulamasıdır (sunucuyu Başlat/Durdur, WebChat'i aç, ayarlar).
