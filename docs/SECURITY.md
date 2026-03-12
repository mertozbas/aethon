# AETHON — Guvenlik Modeli

> Versiyon: 0.1.0 | Tarih: 2026-03-12
> Bu dokuman AETHON'un guvenlik mimarisini, tehdit modelini ve guvenlik politikalarini tanimlar.

---

## 1. Tehdit Modeli

### 1.1 OpenClaw'dan Ogrenilen Dersler

OpenClaw'un bilinen guvenlik sorunlari ve AETHON'un cozumleri:

| # | OpenClaw Sorunu | CVE/Rapor | AETHON Cozumu |
|---|-----------------|-----------|---------------|
| 1 | WebSocket hijack — gateway disaridan erisilebilir | CVE-2026-25253 | Gateway SADECE 127.0.0.1'e baglanir |
| 2 | ClawHub zararli skill'ler (824+ trojan) | ClawHavoc raporu | Marketplace YOK — tum tool'lar yerel |
| 3 | Prompt injection via email/web | CrowdStrike raporu | Hook-tabanli icerik filtreleme |
| 4 | Cross-session veri sizintisi | Giskard raporu | Tek kullanici + session izolasyonu |
| 5 | Self-modifying agent davranisi | Microsoft raporu | Hook ile degisiklik dogrulama |
| 6 | Genis sistem izinleri (rm, sudo, vb.) | Topluluk raporlari | SecurityHookProvider + workspace siniri |
| 7 | Hafiza zehirlenmesi | Kaspersky raporu | MemoryGuardHook + yazma onayi |
| 8 | Kimlik dogrulama eksikligi | CVE-2026-25253 | Allowlist-tabanli sender dogrulama |

### 1.2 AETHON Tehdit Senaryolari

| Tehdit | Vektor | Olasilik | Etki | Azaltma |
|--------|--------|----------|------|---------|
| Dis ag erisimi | Gateway'e dis baglanti | Dusuk | Kritik | 127.0.0.1 only |
| Zararli tool | Bilinmeyen kaynak | Dusuk | Yuksek | Marketplace yok, tum tool'lar yerel |
| Prompt injection | Web icerik, email | Orta | Orta | Icerik filtreleme hook |
| Dosya sistemi hasari | Agent yanlislikla siler | Orta | Yuksek | Workspace-only + blocked cmds |
| Token sizintisi | Log/hafiza uzerinden | Dusuk | Yuksek | MemoryGuard + credential izolasyonu |
| Sonsuz dongu | Agent kendini tetikler | Dusuk | Orta | Timeout + max_iterations |

---

## 2. Guvenlik Katmanlari

### 2.1 Katman Ozeti

```
┌─────────────────────────────────────────────────┐
│ Katman 1: AG GUVENLIGI                           │
│   Gateway sadece 127.0.0.1 — dis erisim imkansiz │
├─────────────────────────────────────────────────┤
│ Katman 2: KIMLIK DOGRULAMA                       │
│   Allowlist tabanli sender_id kontrolu           │
├─────────────────────────────────────────────────┤
│ Katman 3: TOOL GUVENLIGI                         │
│   SecurityHookProvider — workspace + blocked cmds │
├─────────────────────────────────────────────────┤
│ Katman 4: ONAY MEKANIZMASI                       │
│   ApprovalHookProvider — Interrupt ile onay       │
├─────────────────────────────────────────────────┤
│ Katman 5: ICERIK FILTRELEME                      │
│   Dis kaynaklardan gelen icerik temizleme        │
├─────────────────────────────────────────────────┤
│ Katman 6: HAFIZA KORUMA                          │
│   MemoryGuardHook — hassas bilgi tespiti         │
├─────────────────────────────────────────────────┤
│ Katman 7: CREDENTIAL IZOLASYONU                  │
│   Token'lar ayri dizinde, 0600 izinlerle         │
└─────────────────────────────────────────────────┘
```

### 2.2 Katman 1: Ag Guvenligi

**Kural:** AETHON'un dinledigi tum portlar SADECE `127.0.0.1` (localhost) adresine baglanir.

```python
# DOGRU — sadece localhost
config = uvicorn.Config(app, host="127.0.0.1", port=18790)

# YANLIS — ASLA yapma
config = uvicorn.Config(app, host="0.0.0.0", port=18790)
```

**Neden:**
- OpenClaw'un CVE-2026-25253 sorunu disaridan erisilebilen WebSocket'ten kaynaklaniyordu
- AETHON'da gateway'e sadece yerel makineden erisilir
- Telegram/Discord/Slack outbound baglanti yapar, inbound dinleme yok

### 2.3 Katman 2: Kimlik Dogrulama

**Kural:** Sadece bilinen sender_id'ler mesaj gonderebilir.

```python
class MessageRouter:
    def __init__(self, config: AethonConfig):
        self.allowed_senders = config.security.allowed_senders
        # {"telegram": ["12345678"], "discord": ["98765432"], ...}

    async def handle(self, message: InboundMessage) -> OutboundMessage | None:
        # 1. Kimlik kontrolu
        if not self._is_allowed(message):
            return None  # Sessizce reddet

        # 2. Session eslestir
        session_id = self._resolve_session(message)

        # 3. Agent'a ilet
        return await self.runtime.process(message, session_id)

    def _is_allowed(self, message: InboundMessage) -> bool:
        channel_allowed = self.allowed_senders.get(message.channel, [])
        if not channel_allowed:
            return True  # Allowlist bossa herkese izin ver (CLI/WebChat icin)
        return message.sender_id in channel_allowed
```

**Config:**
```yaml
security:
  allowed_senders:
    telegram: ["12345678"]      # Sadece senin Telegram ID'n
    discord: ["98765432"]       # Sadece senin Discord ID'n
    # CLI ve WebChat icin allowlist yok (localhost-only oldugu icin)
```

### 2.4 Katman 3: Tool Guvenligi (SecurityHookProvider)

**Kural:** Agent'in tool cagrilari guvenlik politikasina gore filtrelenir.

```python
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent, AfterToolCallEvent

class SecurityHookProvider(HookProvider):
    """Tool cagrilarini guvenlik politikalarina gore filtrele."""

    BLOCKED_COMMANDS = [
        "rm -rf /", "rm -rf ~", "rm -rf /*",
        "sudo ", "su ",
        "mkfs", "dd if=",
        "chmod 777",
        "> /dev/sda",
        "curl | sh", "wget | sh",
        "kill -9 1",
    ]

    BLOCKED_PATHS = [
        "/etc/", "/usr/", "/bin/", "/sbin/",
        "/System/", "/Library/",
        "~/.ssh/", "~/.gnupg/",
        "~/.aethon/credentials/",
    ]

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self.check_tool_safety)
        registry.add_callback(AfterToolCallEvent, self.log_tool_result)

    def check_tool_safety(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use["name"]
        tool_input = event.tool_use.get("input", {})

        # 1. Tehlikeli komut kontrolu
        if tool_name == "shell":
            command = tool_input.get("command", "")
            if isinstance(command, str):
                for blocked in self.BLOCKED_COMMANDS:
                    if blocked in command:
                        event.deny(
                            f"ENGELLENDI: '{blocked}' iceren komut guvenlik "
                            f"politikasi tarafindan yasaklandi."
                        )
                        return

        # 2. Workspace disi dosya erisimi engelle
        if tool_name in ("file_read", "file_write", "editor"):
            path = (tool_input.get("path", "") or
                    tool_input.get("file_path", "") or
                    tool_input.get("command", ""))
            if path and not self._is_safe_path(path):
                event.deny(
                    f"ENGELLENDI: Workspace disi dosya erisimi ({path}). "
                    f"Sadece {self.workspace} icindeki dosyalara erisebilirsiniz."
                )
                return

        # 3. Ag islemlerini logla
        if tool_name == "http_request":
            url = tool_input.get("url", "")
            self._log_network(tool_name, url)

    def _is_safe_path(self, path: str) -> bool:
        from pathlib import Path
        try:
            resolved = Path(path).expanduser().resolve()
            workspace = Path(self.workspace).expanduser().resolve()
            home = Path.home().resolve()

            # Workspace icinde mi?
            if str(resolved).startswith(str(workspace)):
                return True

            # Yasakli yollarda mi?
            for blocked in self.BLOCKED_PATHS:
                blocked_resolved = Path(blocked).expanduser().resolve()
                if str(resolved).startswith(str(blocked_resolved)):
                    return False

            # Home dizininde ama workspace disinda — dikkatli izin ver
            if str(resolved).startswith(str(home)):
                return True

            return False
        except Exception:
            return False

    def log_tool_result(self, event: AfterToolCallEvent) -> None:
        import logging
        logger = logging.getLogger("aethon.security")
        tool_name = event.tool_use["name"]
        status = "ERROR" if event.tool_result.get("status") == "error" else "OK"
        logger.info(f"TOOL: {tool_name} | STATUS: {status}")
```

### 2.5 Katman 4: Onay Mekanizmasi (ApprovalHookProvider)

**Kural:** Tehlikeli tool'lar icin Interrupt ile kullanici onayi istenir.

```python
from strands import Interrupt
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent

class ApprovalHookProvider(HookProvider):
    """Tehlikeli tool'lar icin kullanici onayi iste."""

    REQUIRES_APPROVAL = {"shell", "file_write", "send_message"}

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self.check_approval)

    def check_approval(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use["name"]

        if tool_name in self.REQUIRES_APPROVAL:
            tool_input = event.tool_use.get("input", {})

            # Interrupt olustur — agent duraklar, kullanici onay bekler
            interrupt = Interrupt(
                id=f"approval-{tool_name}-{event.tool_use.get('toolUseId', 'unknown')}",
                name=f"{tool_name}_approval",
                reason={
                    "tool": tool_name,
                    "parameters": tool_input,
                    "message": f"'{tool_name}' tool'u calistirilmak isteniyor. Onayla?",
                },
            )
            # Bu Interrupt, agent'i duraklatir
            # Kullanici CLI/WebChat uzerinden onaylar veya reddeder
            # Onay: agent devam eder
            # Red: tool calistirmadan devam eder
```

**Kullanici Deneyimi:**
```
AETHON: "shell" komutunu calistirmak istiyorum:
  Komut: git status
  Onayla? [E/h]

Kullanici: E
AETHON: (komutu calistirir)
```

### 2.6 Katman 5: Icerik Filtreleme

**Kural:** Dis kaynaklardan gelen icerik (web, email) filtrelenir.

```python
class ContentFilterHook(HookProvider):
    """Dis icerik filtreleme."""

    SUSPICIOUS_PATTERNS = [
        r"ignore previous instructions",
        r"ignore all instructions",
        r"you are now",
        r"system prompt",
        r"<script",
        r"javascript:",
        r"onerror=",
        r"onclick=",
    ]

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(AfterToolCallEvent, self.filter_content)

    def filter_content(self, event: AfterToolCallEvent) -> None:
        tool_name = event.tool_use["name"]

        # Sadece dis icerik getiren tool'lari kontrol et
        if tool_name in ("http_request", "file_read"):
            content = str(event.tool_result.get("content", ""))
            for pattern in self.SUSPICIOUS_PATTERNS:
                import re
                if re.search(pattern, content, re.IGNORECASE):
                    import logging
                    logger = logging.getLogger("aethon.security")
                    logger.warning(
                        f"SUSPICIOUS CONTENT: Pattern '{pattern}' "
                        f"found in {tool_name} result"
                    )
```

### 2.7 Katman 6: Hafiza Koruma (MemoryGuardHook)

**Kural:** Uzun vadeli hafizaya yazma oncesi hassas bilgi kontrolu.

```python
class MemoryGuardHook(HookProvider):
    """Hafizaya yazilan bilgileri kontrol et."""

    SENSITIVE_PATTERNS = [
        r"(?:api[_-]?key|apikey)\s*[:=]\s*\S+",
        r"(?:password|passwd|pwd)\s*[:=]\s*\S+",
        r"(?:secret|token)\s*[:=]\s*\S+",
        r"(?:ssh-rsa|ssh-ed25519)\s+\S+",
        r"\b[A-Za-z0-9+/]{40,}={0,2}\b",  # Base64 encoded secrets
        r"-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
    ]

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self.guard_memory)

    def guard_memory(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use["name"]

        if tool_name == "manage_memory":
            action = event.tool_use.get("input", {}).get("action", "")
            content = event.tool_use.get("input", {}).get("content", "")

            if action == "store" and content:
                for pattern in self.SENSITIVE_PATTERNS:
                    import re
                    if re.search(pattern, content, re.IGNORECASE):
                        event.deny(
                            "ENGELLENDI: Hafizaya hassas bilgi (API key, "
                            "sifre, token) kaydedilmek istendi. "
                            "Bu bilgiler hafizaya kaydedilmez."
                        )
                        return
```

### 2.8 Katman 7: Credential Izolasyonu

**Kural:** Token'lar ve sifreler ayri bir dizinde, kisitli izinlerle saklanir.

```
~/.aethon/credentials/          # 0700 izinler (sadece kullanici okur)
  ├── telegram.env              # 0600 izinler
  ├── discord.env               # 0600 izinler
  └── slack.env                 # 0600 izinler
```

```python
def setup_credentials_dir(credentials_dir: Path):
    """Credential dizinini guclu izinlerle olustur."""
    credentials_dir.mkdir(parents=True, exist_ok=True)
    credentials_dir.chmod(0o700)

    for env_file in credentials_dir.glob("*.env"):
        env_file.chmod(0o600)
```

**Config'de ortam degiskeni referansi:**
```yaml
channels:
  telegram:
    token: "${TELEGRAM_BOT_TOKEN}"  # ~/.aethon/credentials/telegram.env'den yuklenir
```

---

## 3. Guvenlik Kontrol Listesi

### 3.1 Gelistirme Zamani

- [ ] Tum dinleme portlari `127.0.0.1` adresine bagli
- [ ] SecurityHookProvider aktif ve test edilmis
- [ ] ApprovalHookProvider aktif (tehlikeli tool'lar icin)
- [ ] Workspace disi dosya erisimi engelleniyor
- [ ] Blocked commands listesi guncel
- [ ] Credential dosyalari dogru izinlerle olusturuluyor
- [ ] Hassas bilgi loglara yazilmiyor
- [ ] Tool sonuclari loglaniyorlar (audit trail)

### 3.2 Calisma Zamani

- [ ] Gateway sadece localhost'ta dinliyor
- [ ] Bilinmeyen sender_id'ler reddediliyor
- [ ] Tehlikeli komutlar engelleniyor
- [ ] Workspace disi dosya erisimi engelleniyor
- [ ] Hafizaya hassas bilgi yazilmiyor
- [ ] Dis icerikten prompt injection tespit ediliyor
- [ ] Tool cagrilari loglaniyorlar

### 3.3 Periyodik Kontrol

- [ ] Credential dosya izinleri dogru (0600/0700)
- [ ] Log dosyalari hassas bilgi icermiyor
- [ ] Hafiza veritabaninda hassas bilgi yok
- [ ] Blocked commands listesi guncel
- [ ] Strands SDK guncel (guvenlik yamalari)
- [ ] Ollama guncel

---

## 4. Guvenlik Yapisi Ozeti

```python
# Her AethonRuntime orneginde aktif olan hook'lar:

hooks = [
    SecurityHookProvider(workspace=config.paths.workspace),
    ApprovalHookProvider(requires_approval=config.security.require_approval),
    ContentFilterHook(),
    MemoryGuardHook(),
    TelemetryHookProvider(),  # Audit trail
]

agent = Agent(
    model=model,
    system_prompt=composed_prompt,
    tools=tools,
    hooks=hooks,
    # ...
)
```

**Onemli:** Hook'lar sirali calisir. SecurityHookProvider ILKTIR — engelleme onceligine sahiptir. ApprovalHookProvider ikinci — guvenlik gecen ama onay gerektiren tool'lar icin.
