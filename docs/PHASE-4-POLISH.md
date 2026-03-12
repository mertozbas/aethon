# AETHON — Faz 4: Cilalama + Ileri Ozellikler

> Hedef: Uretim kalitesi, performans optimizasyonu, ileri ozellikler.
> Sure: Surekli gelistirme
> Oncelik: P2 (Guzellestirme)
> Onkosul: Faz 1-3 tamamlanmis

---

## 1. Faz Ozeti

Faz 4 surekli gelistirme fazidir. Her ozellik bagimsiz olarak implement edilebilir.

```
┌──────────────────────────────────────────────────────────────┐
│                     FAZ 4 OZELLIKLERI                         │
│                                                              │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────┐│
│  │Zamanlayici│  │ Dashboard │  │OpenTelemetry│  │   MCP    ││
│  │(APSched)  │  │ (Web UI)  │  │ (Tracing)  │  │(Dis Tool)││
│  └──────────┘  └───────────┘  └────────────┘  └──────────┘│
│                                                              │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────┐│
│  │ Webhook  │  │  Plugin   │  │    Ses     │  │ Auto     ││
│  │(Tetikle) │  │ (Extend)  │  │(Bidi Strm) │  │ Context  ││
│  └──────────┘  └───────────┘  └────────────┘  └──────────┘│
│                                                              │
│  ┌──────────────┐  ┌────────────────┐                       │
│  │  Performans  │  │ Test Suite     │                       │
│  │(Cache,Lazy)  │  │(Unit+Integr)  │                       │
│  └──────────────┘  └────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Ozellik Detaylari

### 2.1 Zamanlayici (APScheduler)

**Dosya:** `aethon/tools/scheduler.py`
**Amac:** Cron-tabanli otomatik SOP tetikleme

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class AethonScheduler:
    """Cron-tabanli gorev zamanlayici."""

    def __init__(self, sop_runner, runtime):
        self.scheduler = AsyncIOScheduler()
        self.sop_runner = sop_runner
        self.runtime = runtime

    def add_job(self, job_id: str, cron: str, sop_name: str):
        """Zamanlanmis SOP gorevi ekle."""
        trigger = CronTrigger.from_crontab(cron)
        self.scheduler.add_job(
            self._run_sop,
            trigger=trigger,
            id=job_id,
            args=[sop_name],
            replace_existing=True,
        )

    async def _run_sop(self, sop_name: str):
        """Zamanlanmis SOP'u calistir."""
        agent = self.runtime.get_or_create_agent("scheduler:cron")
        result = self.sop_runner.run_sop(sop_name, agent)
        # Sonucu varsayilan kanala gonder (config'den)
        # ornegin Telegram'a sabah brifing

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown()
```

**Config:**
```yaml
scheduler:
  enabled: true
  jobs:
    morning_brief:
      cron: "0 9 * * 1-5"      # Hafta ici sabah 9
      sop: morning-brief
    weekly_report:
      cron: "0 18 * * 5"       # Cuma 18:00
      sop: weekly-report
```

**schedule_task Tool:**
```python
@tool
def schedule_task(cron_expression: str, sop_name: str, job_id: str = "") -> str:
    """Zamanlanmis gorev olustur veya guncelle.

    Args:
        cron_expression: Cron ifadesi (orn: "0 9 * * 1-5")
        sop_name: Calistirilacak SOP adi
        job_id: Gorev ID (bos ise otomatik olusturulur)
    """
    scheduler = _get_scheduler_instance()
    if not job_id:
        import uuid
        job_id = f"task-{uuid.uuid4().hex[:8]}"
    scheduler.add_job(job_id, cron_expression, sop_name)
    return f"Gorev zamanlandi: {job_id} → {sop_name} ({cron_expression})"
```

---

### 2.2 send_message Tool

**Dosya:** `aethon/tools/messaging.py`
**Amac:** Agent'in baska kanallara mesaj gondermesi

```python
@tool
def send_message(channel: str, text: str, recipient: str = "") -> str:
    """Belirtilen kanala mesaj gonder.

    Args:
        channel: Hedef kanal ("telegram", "discord", "slack", "webchat")
        text: Gonderilecek mesaj
        recipient: Alici ID (bos ise varsayilan kullanici)
    """
    gateway = _get_gateway_instance()
    adapter = gateway.adapters.get(channel)
    if not adapter:
        return f"Kanal bulunamadi veya etkin degil: {channel}"

    outbound = OutboundMessage(
        channel=channel,
        recipient_id=recipient or "default",
        text=text,
    )
    import asyncio
    asyncio.create_task(adapter.send(outbound))
    return f"Mesaj {channel} uzerinden gonderildi."
```

---

### 2.3 Web Dashboard

**Dosya:** `aethon/ui/`
**Amac:** WebChat adaptorune dashboard ozellikleri ekle

**Endpoint'ler:**

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/` | GET | Chat arayuzu |
| `/dashboard` | GET | Dashboard ana sayfa |
| `/api/status` | GET | Sistem durumu (aktif kanallar, uptime) |
| `/api/sessions` | GET | Aktif session listesi |
| `/api/sessions/{id}` | GET | Session detayi (mesaj gecmisi) |
| `/api/config` | GET | Mevcut yapilandirma |
| `/api/config` | PUT | Yapilandirma guncelle |
| `/api/memory` | GET | Hafiza listesi |
| `/api/memory/search` | POST | Hafiza arama |
| `/api/scheduler/jobs` | GET | Zamanlanmis gorevler |

**Dashboard UI:**
- Vanilla JS + WebSocket (Mert'in tarzina uygun)
- Glassmorphism + Cyberpunk Neon vibes
- Aktif session'lar, kanal durumlari, hafiza istatistikleri
- Gercek zamanli log stream'i

---

### 2.4 TelemetryHookProvider (OpenTelemetry)

**Dosya:** `aethon/agent/hooks/telemetry.py`

```python
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import (
    BeforeToolCallEvent, AfterToolCallEvent,
    BeforeModelCallEvent, AfterModelCallEvent,
)
import time
import logging

class TelemetryHookProvider(HookProvider):
    """Tool ve model cagrilarini izle ve logla."""

    def __init__(self):
        self.logger = logging.getLogger("aethon.telemetry")
        self._timers: dict[str, float] = {}

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)
        registry.add_callback(BeforeModelCallEvent, self.before_model)
        registry.add_callback(AfterModelCallEvent, self.after_model)

    def before_tool(self, event: BeforeToolCallEvent):
        tool_id = event.tool_use.get("toolUseId", "unknown")
        self._timers[f"tool:{tool_id}"] = time.monotonic()
        self.logger.info(f"TOOL START: {event.tool_use['name']}")

    def after_tool(self, event: AfterToolCallEvent):
        tool_id = event.tool_use.get("toolUseId", "unknown")
        elapsed = time.monotonic() - self._timers.pop(f"tool:{tool_id}", time.monotonic())
        status = event.tool_result.get("status", "unknown")
        self.logger.info(f"TOOL END: {event.tool_use['name']} | {elapsed:.2f}s | {status}")

    def before_model(self, event: BeforeModelCallEvent):
        self._timers["model"] = time.monotonic()
        self.logger.debug(f"MODEL START: {len(event.messages)} messages")

    def after_model(self, event: AfterModelCallEvent):
        elapsed = time.monotonic() - self._timers.pop("model", time.monotonic())
        self.logger.info(f"MODEL END: {elapsed:.2f}s | stop={event.stop_reason}")

        # Token kullanimi (varsa)
        if event.metrics:
            usage = getattr(event.metrics, "accumulated_usage", {})
            if usage:
                self.logger.info(
                    f"TOKENS: in={usage.get('inputTokens', '?')} "
                    f"out={usage.get('outputTokens', '?')}"
                )
```

---

### 2.5 MemoryGuardHook

**Dosya:** `aethon/agent/hooks/memory_guard.py`

(SECURITY.md'de detayli tanimlandigi gibi — Katman 6)

---

### 2.6 MCP Sunucu Entegrasyonu

**Dosya:** `aethon/tools/mcp_integration.py`
**Amac:** Dis MCP sunuculardan tool yukleme

```python
from strands.tools.mcp import MCPClient
from mcp import StdioServerParameters, stdio_client

def load_mcp_tools(server_config: dict) -> list:
    """MCP sunucusundan tool'lari yukle."""
    mcp_client = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command=server_config["command"],
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
            )
        )
    )
    mcp_client.__enter__()
    return mcp_client.list_tools_sync()
```

**Config:**
```yaml
mcp_servers:
  - name: "custom-tools"
    command: "python"
    args: ["-m", "my_mcp_server"]
    env: {}
```

---

### 2.7 CONTEXT.md Otomatik Guncelleme

**Dosya:** `aethon/agent/prompt.py` (guncelleme)

```python
class ContextUpdater:
    """CONTEXT.md dosyasini otomatik guncelle."""

    def __init__(self, workspace_dir: str):
        self.context_file = Path(workspace_dir).expanduser() / "CONTEXT.md"

    def update(self, key: str, value: str):
        """Baglam bilgisi ekle/guncelle."""
        content = self.context_file.read_text(encoding="utf-8") if self.context_file.exists() else ""

        # Key:Value formati ile guncelle
        import re
        pattern = rf"^### {re.escape(key)}\n.*?(?=\n### |\Z)"
        replacement = f"### {key}\n{value}"

        if re.search(pattern, content, re.DOTALL | re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.MULTILINE)
        else:
            content += f"\n\n{replacement}"

        self.context_file.write_text(content, encoding="utf-8")
```

---

### 2.8 Webhook Destegi

**Dosya:** `aethon/gateway/webhooks.py`

```python
from fastapi import Request

def setup_webhooks(app, router):
    """Dis tetikleyiciler icin webhook endpoint'leri."""

    @app.post("/webhook/{channel}")
    async def webhook_handler(channel: str, request: Request):
        body = await request.json()
        inbound = InboundMessage(
            channel=f"webhook:{channel}",
            sender_id="webhook",
            sender_name="Webhook",
            text=body.get("text", ""),
            raw=body,
        )
        response = await router.handle(inbound)
        return {"status": "ok", "response": response.text if response else None}
```

---

### 2.9 Performans Optimizasyonu

| Alan | Optimizasyon | Etki |
|------|-------------|------|
| Model | Model warm-up (ilk cagri oncesi dummy istek) | Ilk yanit hizi |
| Tool | Lazy tool import (sadece gerektiginde yukle) | Baslangic suresi |
| Session | Session cache (LRU, son 10 session bellekte) | Yanit hizi |
| Memory | Embedding cache (son N arama bellekte) | Hafiza arama hizi |
| Gateway | Connection pooling (adapter basina) | Ag performansi |

---

### 2.10 Test Suite

**Dosya:** `tests/`

```
tests/
  ├── unit/
  │   ├── test_config.py
  │   ├── test_prompt_composer.py
  │   ├── test_message_router.py
  │   ├── test_session_manager.py
  │   ├── test_vector_memory.py
  │   ├── test_security_hook.py
  │   └── test_sop_runner.py
  ├── integration/
  │   ├── test_cli_adapter.py
  │   ├── test_webchat_adapter.py
  │   ├── test_agent_runtime.py
  │   ├── test_multiagent.py
  │   └── test_full_pipeline.py
  └── conftest.py                # Shared fixtures
```

**Test Araclari:**
- `pytest` + `pytest-asyncio`
- Mock Ollama (yanit simule et)
- Fixture: gecici workspace, config, session

---

## 3. Oncelik Sirasi

Faz 4 ozellikleri bagimsiz implement edilebilir. Onerilen sira:

```
1. TelemetryHookProvider      — Her seyi izle (debug icin kritik)
2. Zamanlayici                 — Sabah brifing ilk onemli otomasyon
3. send_message tool           — Kanal-arasi mesajlasma
4. MemoryGuardHook             — Guvenlik tamamlamasi
5. CONTEXT.md otomatik         — Akilli baglam yonetimi
6. Test Suite                  — Kalite guvencesi
7. Performans optimizasyonu    — Hiz iyilestirmesi
8. Web Dashboard               — Gorsel izleme
9. Webhook destegi             — Dis entegrasyon
10. MCP entegrasyonu           — Dis tool kaynaklari
11. Plugin sistemi             — Genisletilebilirlik (deneysel)
12. Ses destegi                — Bidi streaming (deneysel)
```

---

## 4. Dogrulama Kontrol Listesi

```
[ ] Zamanlayici: Sabah 9'da otomatik brifing tetikleniyor
[ ] send_message: Agent Telegram'a mesaj gonderebiliyor
[ ] Dashboard: localhost:18790/dashboard calisiyor
[ ] TelemetryHook: Tool cagri sureleri loglaniyor
[ ] MemoryGuardHook: API key hafizaya kaydedilmeye calisildiginda engelleniyor
[ ] MCP: Dis MCP sunucudan tool yuklenebiliyor
[ ] CONTEXT.md: Otomatik guncelleniyor
[ ] Webhook: POST /webhook/trigger ile SOP tetiklenebiliyor
[ ] Performans: Basit gorevler <30s icinde yanitlaniyor
[ ] Test: Tum unit testler geciyor
[ ] Test: Entegrasyon testleri geciyor
```
