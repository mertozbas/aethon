# AETHON — Faz 1: Cekirdek Runtime

> Hedef: CLI ve WebChat uzerinden AETHON ile konusabilir hale gelmek.
> Tahmini Sure: 1-2 Hafta
> Oncelik: P0 (Zorunlu)

---

## 1. Faz Ozeti

Faz 1 sonunda su calisir halde olacak:

```
Kullanici (Terminal) ──▶ CLIAdapter ──▶ MessageRouter ──▶ AethonRuntime
                                                              │
Kullanici (Browser)  ──▶ WebChatAdapter ──────────────────────┘
                                                              │
                                                         Strands Agent
                                                         (OllamaModel)
                                                              │
                                                         Tool'lar
                                                     (file_read, shell, vb.)
```

---

## 2. Implementasyon Sirasi

### Adim 1.1: Proje Iskeleti

**Dosyalar:**
- `pyproject.toml`
- `aethon/__init__.py`
- `aethon/__main__.py` (bos placeholder)

**pyproject.toml Icerigi:**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "aethon"
version = "0.1.0"
description = "Personal AI assistant powered by Strands Agents SDK"
requires-python = ">=3.10"

dependencies = [
    # Cekirdek
    "strands-agents>=1.0.0",
    "strands-agents-tools>=0.1.0",

    # Gateway
    "fastapi>=0.100.0",
    "uvicorn>=0.20.0",
    "websockets>=12.0",

    # Config
    "pyyaml>=6.0",
    "pydantic>=2.4.0",

    # CLI
    "prompt-toolkit>=3.0.0",
    "rich>=14.0.0",
    "click>=8.0.0",
]

[project.scripts]
aethon = "aethon.__main__:main"

[project.optional-dependencies]
channels = [
    "aiogram>=3.0.0",
    "discord.py>=2.0.0",
    "slack-bolt>=1.18.0",
]
memory = [
    "aiosqlite>=0.19.0",
]
sops = [
    "strands-agents-sops>=0.1.0",
]
scheduler = [
    "apscheduler>=3.10.0",
]
all = ["aethon[channels,memory,sops,scheduler]"]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

**Paket Yapisi:**
```
aethon/
  ├── pyproject.toml
  ├── aethon/
  │   ├── __init__.py           # __version__ = "0.1.0"
  │   └── __main__.py           # placeholder
  ├── workspace/                 # Varsayilan sablon
  │   ├── SOUL.md
  │   ├── TOOLS.md
  │   └── CONTEXT.md
  └── tests/
      └── __init__.py
```

**Test:** `pip install -e .` basarili olmali.

---

### Adim 1.2: AethonConfig

**Dosya:** `aethon/config.py`

**Amac:** YAML config dosyasini yukle, ortam degiskenlerini coz, Pydantic ile dogrula.

**Pydantic Modeller:**

```python
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional
import os
import yaml

class ModelConfig(BaseModel):
    provider: str = "ollama"                    # "ollama", "openai", "anthropic", "bedrock", "gemini", "litellm", "mistral"
    host: str = "http://localhost:11434"        # Ollama/OpenAI-compat host
    model_id: str = "qwen3-coder-next"          # Model ID (provider'a gore degisir)
    api_key: str = ""                           # API key (OpenAI, Anthropic, Gemini, Mistral icin)
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 40
    max_tokens: int = 8192                      # Max output token
    region: str = "us-west-2"                   # AWS Bedrock region
    extra: dict = Field(default_factory=dict)    # Provider-spesifik ek parametreler

class WebChatChannelConfig(BaseModel):
    enabled: bool = True
    port: int = 18790

class CLIChannelConfig(BaseModel):
    enabled: bool = True

class TelegramChannelConfig(BaseModel):
    enabled: bool = False
    token: str = ""

class DiscordChannelConfig(BaseModel):
    enabled: bool = False
    token: str = ""

class SlackChannelConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    app_token: str = ""

class WhatsAppChannelConfig(BaseModel):
    enabled: bool = False

class ChannelsConfig(BaseModel):
    cli: CLIChannelConfig = CLIChannelConfig()
    webchat: WebChatChannelConfig = WebChatChannelConfig()
    telegram: TelegramChannelConfig = TelegramChannelConfig()
    discord: DiscordChannelConfig = DiscordChannelConfig()
    slack: SlackChannelConfig = SlackChannelConfig()
    whatsapp: WhatsAppChannelConfig = WhatsAppChannelConfig()

class SecurityConfig(BaseModel):
    workspace_only: bool = True
    require_approval: list[str] = Field(default_factory=lambda: ["shell", "file_write", "send_message"])
    blocked_commands: list[str] = Field(default_factory=lambda: ["rm -rf /", "sudo", "mkfs"])
    allowed_senders: dict[str, list[str]] = Field(default_factory=dict)

class SessionConfig(BaseModel):
    storage_dir: str = "~/.aethon/sessions"
    conversation_manager: str = "summarizing"
    summary_ratio: float = 0.3
    preserve_recent_messages: int = 10

class PathsConfig(BaseModel):
    workspace: str = "~/.aethon/workspace"
    sessions: str = "~/.aethon/sessions"
    memory_db: str = "~/.aethon/memory.sqlite"
    logs: str = "~/.aethon/logs"
    credentials: str = "~/.aethon/credentials"

class AethonConfig(BaseModel):
    model: ModelConfig = ModelConfig()
    channels: ChannelsConfig = ChannelsConfig()
    security: SecurityConfig = SecurityConfig()
    session: SessionConfig = SessionConfig()
    paths: PathsConfig = PathsConfig()

    @classmethod
    def load(cls, config_path: str = "~/.aethon/config.yaml") -> "AethonConfig":
        """YAML dosyasindan config yukle."""
        path = Path(config_path).expanduser()
        if path.exists():
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            # Ortam degiskenlerini coz
            raw = cls._resolve_env_vars(raw)
            return cls(**raw)
        return cls()  # Varsayilan degerler

    @staticmethod
    def _resolve_env_vars(data):
        """${VAR_NAME} formatindaki degiskenleri coz."""
        if isinstance(data, str):
            if data.startswith("${") and data.endswith("}"):
                var_name = data[2:-1]
                return os.environ.get(var_name, "")
            return data
        elif isinstance(data, dict):
            return {k: AethonConfig._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AethonConfig._resolve_env_vars(item) for item in data]
        return data
```

**Test:** Config dosyasi olmadan varsayilan degerlerle yuklenebilmeli.

---

### Adim 1.3: Mesaj Modelleri + ChannelAdapter ABC

**Dosya:** `aethon/channels/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class MediaAttachment:
    type: str                          # "image", "audio", "video", "document"
    url: Optional[str] = None
    data: Optional[bytes] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None

@dataclass
class InboundMessage:
    channel: str                       # "cli", "webchat", "telegram", ...
    sender_id: str
    sender_name: str
    text: str
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw: dict = field(default_factory=dict)

@dataclass
class OutboundMessage:
    channel: str
    recipient_id: str
    text: str
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None

class ChannelAdapter(ABC):
    """Tum kanal adapterleri icin temel sinif."""

    def __init__(self, config, router):
        self.config = config
        self.router = router

    @abstractmethod
    async def start(self) -> None:
        """Kanal dinlemeye basla."""

    @abstractmethod
    async def stop(self) -> None:
        """Kanali duzenli kapat."""

    @abstractmethod
    async def send(self, message: OutboundMessage) -> None:
        """Mesaj gonder."""

    async def on_message(self, message: InboundMessage) -> None:
        """Gelen mesaji router'a ilet."""
        response = await self.router.handle(message)
        if response:
            await self.send(response)
```

---

### Adim 1.4: Model Factory (Multi-Provider)

**Dosya:** `aethon/agent/model_factory.py`

**Amac:** Config'deki `provider` alanina gore dogru model sinifini olustur. Config'den `provider: openai` yazildiginda OpenAI, `provider: anthropic` yazildiginda Anthropic modeli olusturulur.

```python
from strands.models import Model

def create_model(config: "ModelConfig") -> Model:
    """Config'e gore uygun model provider'i olustur.

    Desteklenen provider'lar:
    - ollama:    Yerel Ollama (varsayilan)
    - openai:    OpenAI API (GPT-4o, vb.)
    - anthropic: Anthropic API (Claude Sonnet/Opus)
    - bedrock:   AWS Bedrock (Claude, Titan, vb.)
    - gemini:    Google Gemini
    - litellm:   LiteLLM proxy (100+ model)
    - mistral:   Mistral AI
    """
    provider = config.provider.lower()

    if provider == "ollama":
        from strands.models import OllamaModel
        return OllamaModel(
            host=config.host,
            model_id=config.model_id,
            temperature=config.temperature,
            top_p=config.top_p,
            options={"top_k": config.top_k, **config.extra},
        )

    elif provider == "openai":
        from strands.models import OpenAIModel
        client_args = {}
        if config.api_key:
            client_args["api_key"] = config.api_key
        if config.host and config.host != "http://localhost:11434":
            client_args["base_url"] = config.host  # OpenAI-compat sunucular icin
        return OpenAIModel(
            client_args=client_args or None,
            model_id=config.model_id,                # "gpt-4o", "gpt-4o-mini", vb.
            params={"temperature": config.temperature, "max_tokens": config.max_tokens},
        )

    elif provider == "anthropic":
        from strands.models import AnthropicModel
        client_args = {}
        if config.api_key:
            client_args["api_key"] = config.api_key
        return AnthropicModel(
            client_args=client_args or None,
            model_id=config.model_id,                # "claude-sonnet-4-20250514"
            max_tokens=config.max_tokens,
            params={"temperature": config.temperature},
        )

    elif provider == "bedrock":
        from strands.models import BedrockModel
        return BedrockModel(
            model_id=config.model_id,                # "us.anthropic.claude-sonnet-4-20250514-v1:0"
            region=config.region,                    # "us-west-2"
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == "gemini":
        from strands.models import GeminiModel
        return GeminiModel(
            model_id=config.model_id,                # "gemini-2.0-flash"
            client_args={"api_key": config.api_key} if config.api_key else None,
            max_tokens=config.max_tokens,
        )

    elif provider == "litellm":
        from strands.models import LiteLLMModel
        return LiteLLMModel(
            model_id=config.model_id,                # "gpt-4o", "claude-3-opus", vb.
        )

    elif provider == "mistral":
        from strands.models import MistralModel
        return MistralModel(
            model_id=config.model_id,                # "mistral-large-latest"
            client_args={"api_key": config.api_key} if config.api_key else None,
        )

    else:
        raise ValueError(
            f"Bilinmeyen model provider: '{provider}'. "
            f"Desteklenen: ollama, openai, anthropic, bedrock, gemini, litellm, mistral"
        )


def check_model_availability(config: "ModelConfig") -> tuple[bool, str]:
    """Model erisim kontrolu.

    Returns:
        (kullanilabilir_mi, mesaj)
    """
    provider = config.provider.lower()

    if provider == "ollama":
        import requests
        try:
            r = requests.get(f"{config.host}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            if any(config.model_id in m for m in models):
                return True, f"Ollama OK: {config.model_id}"
            return False, (
                f"Model '{config.model_id}' Ollama'da bulunamadi.\n"
                f"  → Mevcut modeller: {', '.join(models)}\n"
                f"  → Indir: ollama pull {config.model_id}"
            )
        except Exception:
            return False, (
                f"Ollama ({config.host}) erisilemez.\n"
                f"  → Baslat: ollama serve"
            )

    elif provider in ("openai", "anthropic", "gemini", "mistral"):
        if not config.api_key:
            return False, (
                f"{provider} icin API key gerekli.\n"
                f"  → config.yaml: model.api_key: 'sk-...'\n"
                f"  → veya: AETHON_{provider.upper()}_API_KEY ortam degiskeni"
            )
        return True, f"{provider} OK: {config.model_id} (API key mevcut)"

    elif provider == "bedrock":
        try:
            import boto3
            boto3.client("bedrock-runtime", region_name=config.region)
            return True, f"Bedrock OK: {config.model_id} ({config.region})"
        except Exception as e:
            return False, f"AWS Bedrock erisim hatasi: {e}"

    elif provider == "litellm":
        return True, f"LiteLLM OK: {config.model_id}"

    return False, f"Bilinmeyen provider: {provider}"
```

**Config Ornekleri:**

```yaml
# Yerel — Ollama (varsayilan)
model:
  provider: ollama
  host: "http://localhost:11434"
  model_id: "qwen3-coder-next"

# Bulut — OpenAI GPT-4o
model:
  provider: openai
  model_id: "gpt-4o"
  api_key: "${OPENAI_API_KEY}"
  max_tokens: 8192

# Bulut — Anthropic Claude
model:
  provider: anthropic
  model_id: "claude-sonnet-4-20250514"
  api_key: "${ANTHROPIC_API_KEY}"
  max_tokens: 8192

# Bulut — AWS Bedrock
model:
  provider: bedrock
  model_id: "us.anthropic.claude-sonnet-4-20250514-v1:0"
  region: "us-west-2"

# Bulut — Google Gemini
model:
  provider: gemini
  model_id: "gemini-2.0-flash"
  api_key: "${GEMINI_API_KEY}"

# Proxy — LiteLLM (herhangi bir model)
model:
  provider: litellm
  model_id: "gpt-4o"  # veya "claude-3-opus" veya baska herhangi biri
```

**Anahtar nokta:** Strands SDK'da Agent sinifinın `model` parametresi `Model` tipinde — tum provider'lar bu base class'i implemente eder. Bu yuzden Agent kodu HICBIR ZAMAN degismez, sadece hangi Model nesnesi verildigini degistirirsin.

---

### Adim 1.5: SystemPromptComposer

**Dosya:** `aethon/agent/prompt.py`

```python
from pathlib import Path
from datetime import datetime

class SystemPromptComposer:
    """Katmanli system prompt olustur."""

    def __init__(self, workspace_dir: str):
        self.workspace = Path(workspace_dir).expanduser()

    def compose(self, session_id: str = "") -> str:
        layers = []

        # 1. SOUL.md — Kisilik
        soul_path = self.workspace / "SOUL.md"
        if soul_path.exists():
            layers.append(f"## Kisilik\n{soul_path.read_text(encoding='utf-8')}")

        # 2. TOOLS.md — Kullanici tercihleri
        tools_path = self.workspace / "TOOLS.md"
        if tools_path.exists():
            layers.append(f"## Kullanici Tercihleri\n{tools_path.read_text(encoding='utf-8')}")

        # 3. CONTEXT.md — Mevcut baglam
        context_path = self.workspace / "CONTEXT.md"
        if context_path.exists():
            layers.append(f"## Mevcut Baglam\n{context_path.read_text(encoding='utf-8')}")

        # 4. SOP listesi (varsa)
        sops_dir = self.workspace / "sops"
        if sops_dir.exists():
            sop_names = [f.stem.removesuffix(".sop") for f in sops_dir.glob("*.sop.md")]
            if sop_names:
                sop_list = "\n".join(f"- /{name}" for name in sop_names)
                layers.append(f"## Kullanilabilir Komutlar\n{sop_list}")

        # 5. Kanal ve session bilgisi
        if session_id:
            layers.append(f"## Aktif Session\n{session_id}")

        # 6. Zaman
        layers.append(f"## Zaman\n{datetime.now().isoformat()}")

        return "\n\n---\n\n".join(layers)
```

---

### Adim 1.6: AethonRuntime

**Dosya:** `aethon/agent/runtime.py` (tam versiyon)

```python
from strands import Agent
from strands.models import Model
from strands.session import FileSessionManager
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import file_read, file_write, editor, shell, think, current_time

from aethon.config import AethonConfig
from aethon.agent.model_factory import create_model
from aethon.agent.prompt import SystemPromptComposer
from aethon.agent.hooks.security import SecurityHookProvider
from aethon.channels.base import InboundMessage

class AethonRuntime:
    """AETHON agent calisma zamani."""

    def __init__(self, config: AethonConfig):
        self.config = config
        self.model = create_model(config.model)  # Multi-provider factory
        self.prompt_composer = SystemPromptComposer(config.paths.workspace)
        self.agents: dict[str, Agent] = {}

    def _get_tools(self) -> list:
        """Faz 1 tool listesi."""
        return [file_read, file_write, editor, shell, think, current_time]

    def _get_hooks(self) -> list:
        """Faz 1 hook listesi."""
        return [
            SecurityHookProvider(
                workspace=self.config.paths.workspace,
                blocked_commands=self.config.security.blocked_commands,
            ),
        ]

    def get_or_create_agent(self, session_id: str) -> Agent:
        """Session icin agent al veya olustur."""
        if session_id not in self.agents:
            system_prompt = self.prompt_composer.compose(session_id)

            session_mgr = FileSessionManager(
                session_id=session_id,
                storage_dir=str(
                    Path(self.config.session.storage_dir).expanduser()
                ),
            )

            conv_mgr = SummarizingConversationManager(
                summary_ratio=self.config.session.summary_ratio,
                preserve_recent_messages=self.config.session.preserve_recent_messages,
            )

            self.agents[session_id] = Agent(
                model=self.model,
                system_prompt=system_prompt,
                tools=self._get_tools(),
                session_manager=session_mgr,
                conversation_manager=conv_mgr,
                hooks=self._get_hooks(),
                agent_id="main",
                name="AETHON",
            )
        return self.agents[session_id]

    def process(self, message: InboundMessage, session_id: str) -> str:
        """Mesaji isle ve yanit dondur."""
        agent = self.get_or_create_agent(session_id)
        result = agent(message.text)

        # AgentResult'tan yanit metnini cikar
        try:
            content = result.message["content"]
            text_parts = [block["text"] for block in content if "text" in block]
            return "\n".join(text_parts) if text_parts else str(result)
        except (KeyError, TypeError, IndexError):
            return str(result)
```

**Onemli Notlar:**
- `agent(message.text)` senkron cagri — Strands Agent dahili olarak async loop calistiriyor
- `FileSessionManager` her session icin ayri instance gerektirir (`session_id` parametresi)
- `SummarizingConversationManager` `summary_ratio=0.3` ile mesajlarin %30'unu ozetler
- Tool'lar `strands_tools` paketinden dogrudan import edilir

---

### Adim 1.7: SecurityHookProvider

**Dosya:** `aethon/agent/hooks/security.py`

(SECURITY.md'de detayli tanimlandigi gibi — Katman 3)

**Onemli:** `event.deny(reason)` metodu yerine, blueprint'teki `event.cancel_tool` kullanilabilir. Strands SDK'da BeforeToolCallEvent'in tam API'sine bakmak gerekebilir. Eger `deny` yoksa, sonucu override ederek engelleme yapilir.

---

### Adim 1.8: MessageRouter

**Dosya:** `aethon/gateway/router.py`

```python
from aethon.channels.base import InboundMessage, OutboundMessage
from aethon.agent.runtime import AethonRuntime
from aethon.config import AethonConfig

class MessageRouter:
    """Mesaj yonlendirme ve session eslestirme."""

    def __init__(self, config: AethonConfig, runtime: AethonRuntime):
        self.config = config
        self.runtime = runtime
        self.allowed_senders = config.security.allowed_senders

    async def handle(self, message: InboundMessage) -> OutboundMessage | None:
        """Gelen mesaji isle."""
        # 1. Kimlik kontrolu
        if not self._is_allowed(message):
            return None

        # 2. Session eslestir
        session_id = self._resolve_session(message)

        # 3. Agent'a ilet
        response_text = self.runtime.process(message, session_id)

        # 4. Yanit olustur
        return OutboundMessage(
            channel=message.channel,
            recipient_id=message.sender_id,
            text=response_text,
        )

    def _is_allowed(self, message: InboundMessage) -> bool:
        """Sender izin kontrolu."""
        channel_allowed = self.allowed_senders.get(message.channel, [])
        if not channel_allowed:
            return True  # Allowlist bossa herkese izin ver
        return message.sender_id in channel_allowed

    def _resolve_session(self, message: InboundMessage) -> str:
        """Mesajdan session ID olustur."""
        if message.thread_id:
            return f"{message.channel}:{message.thread_id}"
        return f"{message.channel}:{message.sender_id}"
```

---

### Adim 1.9: CLIAdapter

**Dosya:** `aethon/channels/cli.py`

```python
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown
from pathlib import Path

from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage

class CLIAdapter(ChannelAdapter):
    """Terminal tabanli chat arayuzu."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.console = Console()
        self.running = False

        # Komut gecmisi dosyasi
        history_path = Path("~/.aethon/cli_history").expanduser()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self.prompt_session = PromptSession(
            history=FileHistory(str(history_path))
        )

    async def start(self) -> None:
        """CLI dinlemeye basla."""
        self.running = True
        self.console.print("[bold cyan]AETHON[/] hazir. Cikmak icin 'exit' yaz.\n")

        while self.running:
            try:
                # prompt_toolkit async mode
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.prompt_session.prompt("sen > ")
                )

                if not user_input or not user_input.strip():
                    continue

                if user_input.strip().lower() in ("exit", "quit", "q"):
                    self.console.print("[dim]Gorusuruz![/]")
                    self.running = False
                    break

                # InboundMessage olustur
                inbound = InboundMessage(
                    channel="cli",
                    sender_id="local",
                    sender_name="User",
                    text=user_input.strip(),
                )

                # Router'a gonder
                self.console.print("[dim]Dusunuyor...[/]")
                response = await self.router.handle(inbound)

                if response:
                    self.console.print()
                    self.console.print(Markdown(response.text))
                    self.console.print()

            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[dim]Gorusuruz![/]")
                self.running = False
                break

    async def stop(self) -> None:
        self.running = False

    async def send(self, message: OutboundMessage) -> None:
        """CLI'da mesaj goster."""
        self.console.print(Markdown(message.text))
```

---

### Adim 1.10: WebChatAdapter

**Dosya:** `aethon/channels/webchat.py`

```python
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage

class WebChatAdapter(ChannelAdapter):
    """FastAPI + WebSocket tabanli web chat."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.app = FastAPI(title="AETHON")
        self.port = config.channels.webchat.port  # 18790
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        async def index():
            return HTMLResponse(self._get_chat_html())

        @self.app.websocket("/ws/chat")
        async def ws_chat(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    data = await websocket.receive_text()
                    inbound = InboundMessage(
                        channel="webchat",
                        sender_id="local",
                        sender_name="User",
                        text=data,
                    )
                    response = await self.router.handle(inbound)
                    if response:
                        await websocket.send_text(response.text)
            except WebSocketDisconnect:
                pass

        @self.app.get("/api/status")
        async def status():
            return {"status": "running", "version": "0.1.0"}

    async def start(self) -> None:
        import uvicorn
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",   # SADECE localhost
            port=self.port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def stop(self) -> None:
        pass

    async def send(self, message: OutboundMessage) -> None:
        pass  # WebSocket dogrudan yanit gonderiyor

    def _get_chat_html(self) -> str:
        """Minimal chat UI HTML."""
        return """<!DOCTYPE html>
<html><head>
<title>AETHON</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: system-ui; background: #0a0a0a; color: #e0e0e0;
         display:flex; justify-content:center; align-items:center; height:100vh; }
  .chat { width:700px; height:90vh; display:flex; flex-direction:column;
          border:1px solid #333; border-radius:12px; overflow:hidden; }
  .header { padding:16px; background:#111; border-bottom:1px solid #333;
            font-size:18px; font-weight:bold; color:#00d4ff; }
  .messages { flex:1; overflow-y:auto; padding:16px; }
  .msg { margin:8px 0; padding:10px 14px; border-radius:8px; max-width:80%; }
  .user { background:#1a3a5c; margin-left:auto; }
  .bot { background:#1a1a2e; }
  .input-area { display:flex; padding:12px; border-top:1px solid #333; background:#111; }
  input { flex:1; padding:10px; border:1px solid #333; border-radius:8px;
          background:#0a0a0a; color:#e0e0e0; font-size:14px; outline:none; }
  button { margin-left:8px; padding:10px 20px; border:none; border-radius:8px;
           background:#00d4ff; color:#000; font-weight:bold; cursor:pointer; }
</style>
</head><body>
<div class="chat">
  <div class="header">AETHON</div>
  <div class="messages" id="msgs"></div>
  <div class="input-area">
    <input id="inp" placeholder="Mesajini yaz..." autofocus>
    <button onclick="send()">Gonder</button>
  </div>
</div>
<script>
const ws = new WebSocket(`ws://${location.host}/ws/chat`);
const msgs = document.getElementById('msgs');
const inp = document.getElementById('inp');

function addMsg(text, cls) {
  const d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.textContent = text;
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
}

ws.onmessage = (e) => addMsg(e.data, 'bot');

function send() {
  const t = inp.value.trim();
  if (!t) return;
  addMsg(t, 'user');
  ws.send(t);
  inp.value = '';
}

inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
</script>
</body></html>"""
```

---

### Adim 1.11: AethonGateway

**Dosya:** `aethon/gateway/server.py`

```python
import asyncio
from aethon.config import AethonConfig
from aethon.agent.runtime import AethonRuntime
from aethon.gateway.router import MessageRouter
from aethon.channels.cli import CLIAdapter
from aethon.channels.webchat import WebChatAdapter

class AethonGateway:
    """AETHON ana gateway sunucusu."""

    def __init__(self, config: AethonConfig):
        self.config = config
        self.runtime = AethonRuntime(config)
        self.router = MessageRouter(config, self.runtime)
        self.adapters = {}

    async def start(self):
        """Etkin kanallari baslat."""
        tasks = []

        # WebChat her zaman aktif
        if self.config.channels.webchat.enabled:
            self.adapters["webchat"] = WebChatAdapter(self.config, self.router)
            tasks.append(self.adapters["webchat"].start())

        # CLI her zaman aktif
        if self.config.channels.cli.enabled:
            self.adapters["cli"] = CLIAdapter(self.config, self.router)
            tasks.append(self.adapters["cli"].start())

        # Faz 2'de diger kanallar buraya eklenecek

        if not tasks:
            raise RuntimeError("Hicbir kanal etkin degil!")

        await asyncio.gather(*tasks)

    async def shutdown(self):
        """Tum adapterleri kapat."""
        for adapter in self.adapters.values():
            await adapter.stop()
```

---

### Adim 1.12: CLI Entry Point

**Dosya:** `aethon/__main__.py`

```python
import asyncio
import click
from pathlib import Path
from rich.console import Console

from aethon.config import AethonConfig
from aethon.gateway.server import AethonGateway

console = Console()

@click.group()
def main():
    """AETHON — Kisisel AI Asistan"""
    pass

@main.command()
@click.option("--config", "-c", default="~/.aethon/config.yaml", help="Config dosya yolu")
def start(config: str):
    """AETHON'u baslat."""
    console.print("[bold cyan]AETHON[/] baslatiliyor...\n")

    # Config yukle
    cfg = AethonConfig.load(config)

    # Workspace olustur (yoksa)
    _ensure_workspace(cfg)

    # Model kontrolu (multi-provider)
    from aethon.agent.model_factory import check_model_availability
    available, msg = check_model_availability(cfg.model)
    if not available:
        console.print(f"[red]HATA:[/] {msg}")
        return

    console.print(f"  Provider: [green]{cfg.model.provider}[/]")
    console.print(f"  Model: [green]{cfg.model.model_id}[/]")
    console.print(f"  WebChat: [green]http://127.0.0.1:{cfg.channels.webchat.port}[/]")
    console.print()

    # Gateway baslat
    gateway = AethonGateway(cfg)
    try:
        asyncio.run(gateway.start())
    except KeyboardInterrupt:
        console.print("\n[dim]AETHON kapatiliyor...[/]")
        asyncio.run(gateway.shutdown())

def _ensure_workspace(config: AethonConfig):
    """Workspace dizinini olustur (yoksa)."""
    workspace = Path(config.paths.workspace).expanduser()
    workspace.mkdir(parents=True, exist_ok=True)

    # Varsayilan SOUL.md
    soul = workspace / "SOUL.md"
    if not soul.exists():
        soul.write_text(
            "# AETHON — Kisilik\n\n"
            "Sen AETHON, Mert'in kisisel AI asistanisin.\n"
            "Mac uzerinde Ollama ile calisiyorsun.\n\n"
            "## Davranis\n"
            "- Turkce ve Ingilizce konusabilirsin.\n"
            "- Kisa ve oz yanit ver.\n"
            "- Hata yaptiginda kabul et ve duzelt.\n",
            encoding="utf-8",
        )

    # Varsayilan TOOLS.md
    tools = workspace / "TOOLS.md"
    if not tools.exists():
        tools.write_text(
            "# Kullanici Tercihleri\n\n"
            "- Python 3.10+ kullan\n"
            "- asyncio + OOP tercih et\n"
            "- Kodda yorum ekleme — kod kendini aciklamali\n",
            encoding="utf-8",
        )

    # CONTEXT.md
    context = workspace / "CONTEXT.md"
    if not context.exists():
        context.write_text(
            "# Mevcut Baglam\n\n"
            "Henuz bir baglam belirlenmedi.\n",
            encoding="utf-8",
        )

    # SOP dizini
    sops_dir = workspace / "sops"
    sops_dir.mkdir(exist_ok=True)

    # Session dizini
    sessions = Path(config.paths.sessions).expanduser()
    sessions.mkdir(parents=True, exist_ok=True)

    # Log dizini
    logs = Path(config.paths.logs).expanduser()
    logs.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    main()
```

---

### Adim 1.13: Varsayilan Workspace Sablonu

**Dosyalar:** `workspace/SOUL.md`, `workspace/TOOLS.md`, `workspace/CONTEXT.md`

Bu dosyalar proje icinde sablon olarak bulunur. Ilk calistirmada `~/.aethon/workspace/` dizinine kopyalanir.

---

### Adim 1.14: Entegrasyon Testi

**Dosya:** `tests/test_core.py`

```python
import pytest
from aethon.config import AethonConfig
from aethon.agent.prompt import SystemPromptComposer

def test_config_defaults():
    """Varsayilan config yukleniyor."""
    config = AethonConfig()
    assert config.model.provider == "ollama"
    assert config.model.model_id == "qwen3-coder-next"
    assert config.channels.webchat.port == 18790

def test_config_env_resolve():
    """Ortam degiskeni cozuluyor."""
    import os
    os.environ["TEST_TOKEN"] = "abc123"
    result = AethonConfig._resolve_env_vars("${TEST_TOKEN}")
    assert result == "abc123"

def test_prompt_composer(tmp_path):
    """System prompt birlesiyor."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test kisilik")
    (workspace / "TOOLS.md").write_text("Test tercihler")

    composer = SystemPromptComposer(str(workspace))
    prompt = composer.compose("test-session")
    assert "Test kisilik" in prompt
    assert "Test tercihler" in prompt
    assert "test-session" in prompt
```

---

## 3. Dogrulama Kontrol Listesi

Faz 1 tamamlandiginda:

```
[ ] pip install -e . basarili
[ ] aethon start komutu calisiyor
[ ] Ollama baglanti kontrolu calisiyor
[ ] CLI'da mesaj gonderip yanit alabiliyoruz
[ ] WebChat'te (localhost:18790) mesaj gonderip yanit alabiliyoruz
[ ] Agent file_read tool'unu kullanabiliyor
[ ] Agent shell tool'unu kullanabiliyor (workspace icinde)
[ ] Workspace disi dosya erisimi SecurityHookProvider tarafindan engelleniyor
[ ] "rm -rf /" gibi tehlikeli komutlar engelleniyor
[ ] Konusma gecmisi korunuyor (session)
[ ] Config dosyasi yoksa varsayilan degerlerle calisiyor
[ ] SOUL.md, TOOLS.md system prompt'a dahil ediliyor
[ ] tests/ altindaki testler geciyor
```
