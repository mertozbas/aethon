# Strands Agents SDK - Kapsamli Teknik Referans Dokumani

> Son guncelleme: 2026-03-12
> Kaynaklar: SDK Kaynak Kodu, Resmi Dokumantasyon, AWS Blog, Ornekler, Tools Paketi

---

## 1. GENEL BAKIS

Strands Agents, **model-driven, code-first** bir yaklasimla AI agent'lari olusturmak icin tasarlanmis acik kaynakli bir SDK'dir. AWS tarafindan gelistirilmis, Apache 2.0 lisansli bir projedir.

- **Lisans:** Apache 2.0
- **Dil:** Python 3.10+ (birincil), TypeScript (deneysel)
- **Yaratici:** AWS (Accenture, Anthropic, Meta, PwC katkilari ile)
- **Felsefe:** "Model-driven" — LLM'in planlama ve tool secimini otonom yapmasina guven
- **Web:** https://strandsagents.com
- **GitHub:** https://github.com/strands-agents/sdk-python

### 1.1 Temel Prensip

Strands, karmasik workflow tanimlari yerine **uc temel bilesenle** agent olusturur:

```
Agent = Model + System Prompt + Tools
```

LLM'in kendi akil yurume yetenekleri planlama, tool zincirleme ve yansitma (reflection) icin kullanilir.

### 1.2 Kurulum

```bash
# Temel SDK
pip install strands-agents

# Onceden hazir tool'lar (30+)
pip install strands-agents-tools

# Agent SOP'lari
pip install strands-agents-sops

# Belirli model provider'lar
pip install strands-agents[anthropic]
pip install strands-agents[openai]
pip install strands-agents[ollama]
pip install strands-agents[litellm]
```

---

## 2. MIMARI

### 2.1 Agent Loop (Cekirdek Dongu)

```
Kullanici Girdisi → Context Assembly → Model Inference → Tool Secimi → Tool Calistirma → (Tekrar) → Sonuc
```

**Dongu Detayi:**
1. Bekleyen interrupt veya tool use kontrolu
2. Tool use yoksa: Model'e mesajlar + tool'lar + system prompt gonder
3. Model yanitini isle:
   - `tool_use` → Tool'lari calistir, sonuclari ekle, tekrar donguye gir
   - `end_turn` → Kullaniciya don
   - `max_tokens` → MaxTokensReachedException firlat
4. Hata durumlarinda retry/recovery mantigi
5. Metrik ve tamamlanma eventi yayinla

**Sabitler:**
- `MAX_ATTEMPTS = 6` (throttle hatalarinda maks tekrar)
- `INITIAL_DELAY = 4` saniye (ilk backoff)
- `MAX_DELAY = 240` saniye (maks backoff — 4 dakika)

### 2.2 Bilesem Mimarisi

```
+------------------+
|     Agent        |  → Orkestrasyon motoru
+--------+---------+
         |
    +----+----+----+----+----+
    |         |         |    |
+---+---+ +--+--+ +---+--+ +--+---+
| Model | |Tools| |Hooks | |Session|
+-------+ +-----+ +------+ +------+
    |         |
+---+---+ +--+--+
|Provider| | MCP |
+-------+ +-----+
```

---

## 3. AGENT SINIFI (Cekirdek API)

### 3.1 Constructor

```python
class Agent(AgentBase):
    def __init__(
        self,
        model: Model | str | None = None,           # Model provider veya string ID
        messages: Messages | None = None,             # Baslangic mesaj gecmisi
        tools: list[...] | None = None,               # Tool listesi
        system_prompt: str | list[SystemContentBlock] | None = None,
        structured_output_model: type[BaseModel] | None = None,  # Pydantic model
        callback_handler: Callable | None = _DEFAULT,  # Cikti callback
        conversation_manager: ConversationManager | None = None,
        record_direct_tool_call: bool = True,
        load_tools_from_directory: bool = False,       # ./tools/ dizininden otomatik yukle
        trace_attributes: Mapping[str, AttributeValue] | None = None,  # OpenTelemetry
        concurrent_invocation_mode: ConcurrentInvocationMode = ConcurrentInvocationMode.THROW,
        session_manager: SessionManager | None = None,
        hooks: list[HookProvider] | None = None,
        plugins: list[Plugin] | None = None,
        id: str = "strands-agent",
        name: str = "Strands Agent",
        **kwargs: Any
    ) -> None:
```

### 3.2 Temel Metodlar

```python
# Senkron cagri
result: AgentResult = agent("Merhaba, ne yapabilirsin?")

# Asenkron cagri
result = await agent.invoke_async("Bir dosya olustur")

# Streaming
async for event in agent.stream_async("Anlat"):
    if event.get("type") == "text":
        print(event["text"], end="", flush=True)

# Yapilandirilmis cikti
result = agent("Plan yap", structured_output_model=MyPydanticModel)
plan = result.structured_output

# Dogrudan tool cagirma
agent.tool.calculator(expression="2+3")

# Session yukleme
agent2 = Agent(session_manager=session_mgr).with_session("my-session-id")

# Hook ekleme
agent.add_hook(BeforeToolCallEvent, my_callback)
```

### 3.3 AgentResult Yapisi

```python
@dataclass
class AgentResult:
    stop_reason: StopReason       # "end_turn" | "tool_use" | "max_tokens"
    message: Message              # Agent'in son mesaji
    metrics: EventLoopMetrics     # Token kullanimi, gecikme vb.
    state: Any                    # Guncellenmis agent state
    interrupts: Sequence[Interrupt] | None = None
    structured_output: BaseModel | None = None
```

### 3.4 Stop Reasons

| Neden | Aciklama |
|-------|----------|
| `end_turn` | Agent yaniti tamamladi |
| `tool_use` | Tool cagirma gerekiyor |
| `max_tokens` | Token limiti asildi |
| `stop_sequence` | Durdurma dizisi tespit edildi |
| `content_filtered` | Icerik filtrelendi |
| `guardrail_intervention` | Guvenlik korumasi devreye girdi |

---

## 4. MODEL PROVIDERS

### 4.1 Desteklenen Providerlar

| Provider | Sinif | Varsayilan | Python | TypeScript |
|----------|-------|-----------|--------|------------|
| **AWS Bedrock** | `BedrockModel` | EVET | Tam | Tam |
| **Anthropic** | `AnthropicModel` | - | Tam | - |
| **OpenAI** | `OpenAIModel` | - | Tam | Tam |
| **Ollama** | `OllamaModel` | - | Tam | - |
| **Google Gemini** | `GeminiModel` | - | Tam | Deneysel |
| **LiteLLM** | `LiteLLMModel` | - | Tam | - |
| **LlamaAPI** | `LlamaAPIModel` | - | Tam | - |
| **LlamaCpp** | `LlamaCppModel` | - | Tam | - |
| **Mistral** | `MistralModel` | - | Tam | - |
| **SageMaker** | `SageMakerModel` | - | Tam | - |
| **Writer** | `WriterModel` | - | Tam | - |
| **Cohere** | OpenAI uyumlu | - | Topluluk | - |

### 4.2 Model Base Class

```python
class Model(ABC):
    @abstractmethod
    def update_config(self, **model_config: Any) -> None: ...

    @abstractmethod
    def get_config(self) -> Any: ...

    @abstractmethod
    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]: ...

    @abstractmethod
    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]: ...
```

### 4.3 Ollama Provider (DETAYLI)

```python
from strands.models.ollama import OllamaModel

class OllamaModel(Model):
    class OllamaConfig(TypedDict, total=False):
        model_id: str              # "qwen3-coder-next", "llama3.2:3b", vb.
        max_tokens: int | None
        temperature: float | None
        top_p: float | None
        stop_sequences: list[str] | None
        options: dict[str, Any] | None   # Ek model parametreleri
        keep_alive: str | None           # Bellekte tutma suresi ("5m", "1h")
        additional_args: dict[str, Any] | None

    def __init__(
        self,
        host: str | None = None,           # "http://localhost:11434"
        ollama_client_args: dict[str, Any] | None = None,
        **model_config: Unpack[OllamaConfig]
    ) -> None: ...
```

**Kullanim Ornegi:**
```python
from strands import Agent
from strands.models.ollama import OllamaModel

model = OllamaModel(
    host="http://localhost:11434",
    model_id="qwen3-coder-next",
    temperature=1.0,
    top_p=0.95,
    options={"top_k": 40}
)

agent = Agent(
    model=model,
    system_prompt="Sen bir yazilim gelistirme asistanisin.",
    tools=[my_tool1, my_tool2]
)

result = agent("Bir Python fonksiyonu yaz")
```

**CLI ile Ollama Kullanimi:**
```bash
strands --model-provider ollama --model-config '{"model_id": "qwen3-coder-next"}'
```

**Ortam Degiskeni:**
```bash
export OLLAMA_HOST=http://localhost:11434
```

### 4.4 Ozel Provider Olusturma

```python
from strands.models import Model

class MyCustomModel(Model):
    def update_config(self, **config): ...
    def get_config(self): ...
    async def stream(self, messages, tool_specs=None, ...): ...
    async def structured_output(self, output_model, prompt, ...): ...
```

---

## 5. TOOL SISTEMI

### 5.1 Tool Tanimlama Yontemleri

#### A. Decorator ile (@tool)

```python
from strands import tool

@tool
def calculator(expression: str) -> dict:
    """Matematiksel ifadeyi hesapla.

    Args:
        expression: Hesaplanacak ifade (orn: "2 + 3 * 4")
    """
    return {
        "status": "success",
        "content": [{"text": f"Sonuc: {eval(expression)}"}]
    }
```

#### B. Context Injection ile

```python
from strands import tool
from strands.tools import ToolContext

@tool(context="ctx")
def tool_with_context(param: str, ctx: ToolContext) -> dict:
    """Agent ve invocation state'e erisim."""
    agent = ctx.agent
    tool_use = ctx.tool_use
    invocation_state = ctx.invocation_state
    return {"status": "success", "content": [{"text": "Ok"}]}
```

#### C. Modul Tabanli

```python
# my_tool.py — SDK bagimliligi yok
TOOL_SPEC = {
    "name": "my_tool",
    "description": "Benim tool'um",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Girdi"}
            },
            "required": ["input"]
        }
    }
}

def my_tool(tool_use):
    return {"status": "success", "content": [{"text": "Sonuc"}]}
```

#### D. MCP (Model Context Protocol)

```python
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

mcp_client = MCPClient(
    lambda: stdio_client(StdioServerParameters(
        command="uvx",
        args=["my-mcp-server@latest"]
    )),
    startup_timeout=30,
    tool_filters={"allowed": ["tool1", "tool2"]},
    prefix="my_prefix"
)

with mcp_client:
    agent = Agent(tools=mcp_client.list_tools_sync())
```

### 5.2 Tool Kaynak Cesitleri

Agent'a tool verilirken su formatlari kabul eder:
- `@tool` dekoratorlu fonksiyonlar
- `ToolProvider` ornekleri (MCP client'lar)
- Modul yollari: `"my.module.tool"` veya `"my.module.tool:specific_function"`
- Dosya yollari: `"./path/to/tool.py"`
- Sozlukler: `{"name": "...", "path": "..."}`
- Bunlarin ic ice listeleri

### 5.3 Tool Spec Yapisi

```python
class ToolSpec(TypedDict):
    name: str                      # Benzersiz tool adi
    description: str               # Tool'un ne yaptigi
    inputSchema: JSONSchema        # Girdi parametreleri icin JSON Schema
    outputSchema: NotRequired[JSONSchema]  # Opsiyonel cikti semasi
```

### 5.4 Tool Result Yapisi

```python
class ToolResult(TypedDict):
    toolUseId: str                          # Tool cagri ID'si
    status: Literal["success", "error"]     # Durum
    content: list[ToolResultContent]        # Icerik (text, json, image, document)
```

### 5.5 Tool Calistiricilari (Executors)

| Executor | Aciklama |
|----------|----------|
| `SequentialToolExecutor` | Tool'lari sirayla calistirir (varsayilan) |
| `ConcurrentToolExecutor` | Birden fazla tool'u paralel calistirir (max_workers ile) |

### 5.6 Hot Reload

```python
agent = Agent(load_tools_from_directory=True)  # ./tools/ dizinini izler
```

---

## 6. ONCEDEN HAZIR TOOL'LAR (strands-agents-tools)

### 6.1 Dosya Islemleri

| Tool | Aciklama |
|------|----------|
| `file_read` | Gelismis dosya okuma (view, find, lines, chunk, search, stats, preview, diff, time_machine) |
| `file_write` | Guvenli dosya yazma (onay mekanizmasi ile) |
| `editor` | Gelismis dosya duzenleme (pattern degistirme, coklu dosya) |

### 6.2 Shell ve Sistem

| Tool | Aciklama |
|------|----------|
| `shell` | PTY destekli interaktif shell (gercek zamanli komut calistirma) |
| `python_repl` | Kalici durumlu Python kod calistirma |
| `environment` | Ortam degiskeni yonetimi |
| `current_time` | Herhangi bir zaman diliminde mevcut saat |

### 6.3 Web ve API

| Tool | Aciklama |
|------|----------|
| `http_request` | Cok-auth destekli HTTP istemci (Bearer, SigV4, JWT, vb.) |
| `tavily_search` | LLM-optimize edilmis web arama |
| `tavily_extract` | Web icerik cikarma |
| `tavily_crawl` | Akilli web tarama |
| `exa_search` | Neural/keyword hibrit arama |

### 6.4 Matematik ve Analitik

| Tool | Aciklama |
|------|----------|
| `calculator` | SymPy tabanli matematik (evaluate, solve, derive, integrate, limit, series, matrix) |

### 6.5 Hafiza ve Bilgi Tabani

| Tool | Aciklama |
|------|----------|
| `memory` | Bedrock Knowledge Base (semantic search) |
| `agent_core_memory` | Amazon Bedrock Agent Core Memory |
| `mem0_memory` | Mem0 hafiza yonetimi (OpenSearch ile) |
| `mongodb_memory` | MongoDB Atlas hafiza |
| `elasticsearch_memory` | Elasticsearch hafiza |
| `retrieve` | Bedrock Knowledge Base semantik arama |

### 6.6 Kod Calistirma

| Tool | Aciklama |
|------|----------|
| `code_interpreter` | Izole sandbox'ta kod calistirma (Python, JS, TS) |
| `agent_core_code_interpreter` | AWS Bedrock AgentCore kod yorumlayici |

### 6.7 Tarayici ve Otomasyon

| Tool | Aciklama |
|------|----------|
| `browser` | Playwright tabanli tarayici kontrolu |
| `agent_core_browser` | Bedrock AgentCore tarayici (uzak CDP) |
| `use_computer` | Masaustu otomasyonu (fare, klavye, ekran goruntusu) |

### 6.8 Icerik Uretimi

| Tool | Aciklama |
|------|----------|
| `generate_image` | AI gorsel uretimi |
| `generate_image_stability` | Stability AI gorsel uretimi |
| `image_reader` | Gorsel analizi |
| `nova_reels` | Amazon Nova video uretimi |
| `speak` | Metin-konusma (Polly entegrasyonu) |
| `diagram` | AWS bulut, ag, UML diyagramlari (14+ tip) |

### 6.9 Coklu-Agent ve Koordinasyon

| Tool | Aciklama |
|------|----------|
| `swarm` | Birden fazla uzman agent koordinasyonu |
| `batch` | Paralel tool calistirma |
| `use_agent` | Baska agent'lara gorev delegasyonu |
| `use_llm` | Ozel prompt ile ic ice LLM dongusu |

### 6.10 Dusunme ve Akil Yurutme

| Tool | Aciklama |
|------|----------|
| `think` | Cok-dongulu recursive dusunme (1-10 dongu, model degistirme destegi) |

### 6.11 Iletisim

| Tool | Aciklama |
|------|----------|
| `slack` | Slack entegrasyonu (Socket Mode, otomatik yanit, thread) |

### 6.12 AWS Entegrasyonu

| Tool | Aciklama |
|------|----------|
| `use_aws` | Tum AWS servislerine boto3 uzerinden erisim |
| `a2a_client` | A2A-uyumlu agent'larla iletisim |

### 6.13 Veri ve Dokuman

| Tool | Aciklama |
|------|----------|
| `bright_data` | Web scraping ve veri cikarma |
| `journal` | Yapilandirilmis kayit tutma |
| `rss` | RSS feed yonetimi |

### 6.14 Is Akisi ve Kontrol

| Tool | Aciklama |
|------|----------|
| `workflow` | Cok-adimli otomatik is akislari |
| `stop` | Agent calistirmayi nazikce sonlandir |
| `handoff_to_user` | Insana kontrol devret |
| `load_tool` | Calisma zamaninda dinamik tool yukleme |

---

## 7. HOOKS SISTEMI

### 7.1 Event Tipleri

| Event | Tetiklenme | Degistirilebilir Alanlar |
|-------|-----------|------------------------|
| `AgentInitializedEvent` | Agent olusturulduktan sonra | - |
| `BeforeInvocationEvent` | Agent girdi islemeden once | `messages` |
| `AfterInvocationEvent` | Agent tamamlandiktan sonra | `resume` (yeni girdi ile devam) |
| `MessageAddedEvent` | Konusmaya mesaj eklendikten sonra | - |
| `BeforeModelCallEvent` | Model cagrisindan once | - |
| `AfterModelCallEvent` | Model cagrisindan sonra | `retry` (tekrar dene) |
| `BeforeToolCallEvent` | Tool calistirmadan once | `cancel_tool`, `selected_tool`, `tool_use` |
| `AfterToolCallEvent` | Tool calistirmadan sonra | `result`, `retry` |

### 7.2 Multi-Agent Hook Eventleri

| Event | Tetiklenme |
|-------|-----------|
| `MultiAgentInitializedEvent` | Multi-agent sistemi baslatildiginda |
| `BeforeMultiAgentInvocationEvent` | Multi-agent cagrisindan once |
| `AfterMultiAgentInvocationEvent` | Multi-agent cagrisindan sonra |
| `BeforeNodeCallEvent` | Node (agent) calistirmadan once |
| `AfterNodeCallEvent` | Node calistirmadan sonra |

### 7.3 Hook Kaydetme Yontemleri

```python
# Yontem 1: Dogrudan callback
def my_hook(event: BeforeModelCallEvent) -> None:
    print("Model cagirilacak")

agent.add_hook(BeforeModelCallEvent, my_hook)

# Yontem 2: Tip hint ile cikarim
agent.add_hook(None, my_hook)  # BeforeModelCallEvent tip hint'inden cikarilir

# Yontem 3: HookProvider (yeniden kullanilabilir)
class MyHookProvider(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeModelCallEvent, self.on_before_call)
        registry.add_callback(AfterToolCallEvent, self.on_after_tool)

    def on_before_call(self, event: BeforeModelCallEvent) -> None:
        print("Model cagirilmadan once")

    def on_after_tool(self, event: AfterToolCallEvent) -> None:
        if event.exception:
            event.retry = True  # Basarisiz tool'u tekrar dene

agent = Agent(hooks=[MyHookProvider()])
```

### 7.4 Yasam Dongusu Sirasi

```
BeforeInvocationEvent
  → MessageAddedEvent (kullanici mesaji)
    → BeforeModelCallEvent
      → [Model Cikti Streaming]
    → AfterModelCallEvent
      → MessageAddedEvent (asistan mesaji)
        → BeforeToolCallEvent
          → [Tool Calistirma]
        → AfterToolCallEvent
          → MessageAddedEvent (tool sonucu)
            → [Yeni model dongusu...]
→ AfterInvocationEvent
```

---

## 8. MULTI-AGENT DESENLERI

### 8.1 Uc Temel Desen

| Ozellik | Graph | Swarm | Workflow |
|---------|-------|-------|----------|
| **Konsept** | Gelistirici tanimli akis diyagrami | Dinamik takim devir teslim | On-tanimli gorev DAG |
| **Yapi** | Node + edge onceden tanimli | Agent havuzu, dinamik yol | Sabit bagimliliklar |
| **Calistirma** | Kontrollu ama dinamik | Sirali ve otonom | Deterministik ve paralel |
| **Donguler** | Evet | Evet | Hayir |
| **Durum Paylasimi** | Tek paylasimli dict | Paylasimli context (tam gecmis) | Gorev ciktilari → girdiler |

### 8.2 Swarm (Isbirlikci Takim)

```python
from strands.multiagent import Swarm

swarm = Swarm(
    nodes=[agent1, agent2, agent3],
    entry_point=agent1,           # Baslangic agent'i
    max_handoffs=20,              # Maks agent gecisi
    max_iterations=20,            # Maks dongu
    execution_timeout=900.0,      # Zaman asimi (saniye)
    node_timeout=300.0,           # Agent basina zaman asimi
    session_manager=session_mgr,  # Opsiyonel
    hooks=[my_hook_provider],     # Opsiyonel
)

result = swarm("Bu gorevi tamamla")
```

**Swarm Akisi:**
1. Entry point agent gorevi alir
2. Agent isler, gerekirse baska agent'a devir teslim yapar
3. Tum agent'lar `SharedContext` uzerinden koordine olur
4. max_handoffs/timeout/tamamlanma'ya kadar devam eder

### 8.3 Graph (Deterministik Orkestrasyon)

```python
from strands.multiagent import GraphBuilder

builder = GraphBuilder()

researcher = builder.add_node(research_agent, node_id="researcher")
writer = builder.add_node(writer_agent, node_id="writer")
reviewer = builder.add_node(reviewer_agent, node_id="reviewer")

builder.add_edge(researcher, writer)
builder.add_edge(writer, reviewer)
builder.add_edge(reviewer, writer, condition=lambda state: state["needs_revision"])
builder.set_entry_points(researcher)

graph = builder.build()
result = graph("Bir makale yaz")
```

**Graph Ozellikleri:**
- DAG (yonlu asiklik cizge) sirasiyla calistirma
- Kosullu edge'ler (GraphState degerlendirmesi)
- Dongu destegi (feedback loop'lar)
- Ic ice graph destegi (nested graphs)

### 8.4 Agent-as-Tool Deseni

```python
@tool
def code_generator(task: str) -> str:
    """Kod uretme uzmani."""
    specialist = Agent(
        system_prompt="Sen bir Python kod uzmanisin.",
        model=model
    )
    return specialist(f"Kod yaz: {task}")

main_agent = Agent(tools=[code_generator, code_reviewer])
```

### 8.5 MultiAgentResult Yapisi

```python
@dataclass
class MultiAgentResult:
    status: Status                        # COMPLETED, FAILED, INTERRUPTED
    results: dict[str, NodeResult]        # Node basina sonuclar
    accumulated_usage: Usage              # Toplam token
    accumulated_metrics: Metrics           # Toplam gecikme
    execution_count: int
    execution_time: int                   # Toplam ms
    interrupts: list[Interrupt]

@dataclass
class NodeResult:
    result: AgentResult | MultiAgentResult | Exception
    execution_time: int = 0
    status: Status = Status.PENDING
    accumulated_usage: Usage
    accumulated_metrics: Metrics
    execution_count: int = 0
```

---

## 9. SESSION YONETIMI

### 9.1 SessionManager Arayuzu

```python
class SessionManager(HookProvider, ABC):
    def initialize(self, agent: Agent, **kwargs) -> None: ...
    def append_message(self, message: Message, agent: Agent, **kwargs) -> None: ...
    def sync_agent(self, agent: Agent, **kwargs) -> None: ...
    def initialize_multi_agent(self, source: MultiAgentBase, **kwargs) -> None: ...
    def sync_multi_agent(self, source: MultiAgentBase, **kwargs) -> None: ...
```

### 9.2 Mevcut Implementasyonlar

| Manager | Depolama | Kullanim |
|---------|----------|---------|
| `FileSessionManager` | Yerel dosya sistemi | Gelistirme, tek makine |
| `S3SessionManager` | AWS S3 | Bulut, olceklenebilir |
| `RepositorySessionManager` | Ozel backend | Veritabani, dis API'lar |

### 9.3 Kullanim

```python
from strands.session import FileSessionManager

session_mgr = FileSessionManager(base_dir="./sessions")
agent = Agent(session_manager=session_mgr, id="my-agent")

# Ilk cagri — session olusturur
result = agent("Merhaba")

# Onceki session'dan yukle
agent2 = Agent(session_manager=session_mgr).with_session("my-agent")
result2 = agent2("Nerede kalmistik?")
```

---

## 10. KONUSMA YONETIMI

### 10.1 Mevcut Stratejiler

| Strateji | Aciklama |
|----------|----------|
| `NullConversationManager` | Hicbir sey yapma — tum mesajlari tut |
| `SlidingWindowConversationManager` | Son N mesaji tut (varsayilan) |
| `SummarizingConversationManager` | Eski mesajlari ozetle |

### 10.2 SlidingWindow Yapilandirmasi

```python
from strands.agent.conversation_manager import SlidingWindowConversationManager

agent = Agent(
    conversation_manager=SlidingWindowConversationManager(max_messages=50)
)
```

### 10.3 Summarizing Yapilandirmasi

```python
from strands.agent.conversation_manager import SummarizingConversationManager

agent = Agent(
    conversation_manager=SummarizingConversationManager(
        max_messages=50,
        summary_ratio=0.5,              # Yuzde 50'yi ozetle
        preserve_recent_messages=10,    # Son 10 mesaji koru
        summarizer_model=my_model       # Opsiyonel: ozet icin farkli model
    )
)
```

---

## 11. YAPILANDIRILMIS CIKTI (Structured Output)

```python
from pydantic import BaseModel
from strands import Agent

class TravelPlan(BaseModel):
    destination: str
    duration_days: int
    activities: list[str]
    estimated_cost: float

agent = Agent(structured_output_model=TravelPlan)
result = agent("5 gunluk Japonya seyahati planla")

plan: TravelPlan = result.structured_output
print(f"Hedef: {plan.destination}, Maliyet: ${plan.estimated_cost}")
```

**Isleyis:**
1. Pydantic modeli otomatik olarak tool spec'e donusturulur
2. Model bu tool'u kullanmazsa, agent zorlar
3. Yanit Pydantic semasina gore dogrulanir
4. Dogrulama hatalari model'e duzeltme icin geri gonderilir

---

## 12. INTERRUPTS (Insan-Dongusu)

```python
from strands.interrupt import Interrupt, InterruptException
from strands.hooks import BeforeToolCallEvent

def require_approval(event: BeforeToolCallEvent) -> None:
    if event.tool_use["name"] == "delete_database":
        interrupt = Interrupt(
            id="delete-approval",
            name="Veritabani Silme Onayi",
            reason=f"Silinecek: {event.tool_use['input']}",
        )
        raise InterruptException(interrupt)

agent = Agent()
agent.add_hook(BeforeToolCallEvent, require_approval)

try:
    result = agent("Uretim veritabanimi sil")
except InterruptException as e:
    print(f"Onay gerekli: {e.interrupt.reason}")
    e.interrupt.response = "Evet, sil"
    result = agent([{
        "interruptResponse": {
            "interruptId": e.interrupt.id,
            "response": "Evet"
        }
    }])
```

---

## 13. PLUGIN SISTEMI

```python
from strands.plugins import Plugin, hook
from strands import tool
from strands.hooks import BeforeModelCallEvent

class MyPlugin(Plugin):
    name = "my-plugin"

    @hook  # Otomatik kesfedilir
    def on_before_model(self, event: BeforeModelCallEvent) -> None:
        event.invocation_state["custom_data"] = "value"

    @tool  # Otomatik kesfedilir
    def my_tool(self, param: str) -> dict:
        return {"status": "success", "content": [{"text": f"Islendi: {param}"}]}

    def init_agent(self, agent: "Agent") -> None:
        pass  # Opsiyonel baslangic mantigi

agent = Agent(plugins=[MyPlugin()])
```

---

## 14. AGENT SOP'LARI (Standard Operating Procedures)

### 14.1 Nedir?

SOP'lar, AI agent'lari karmasik gorevlerde yonlendiren **markdown tabanli talimat setleridir** (`.sop.md`).

### 14.2 Mevcut SOP'lar

| SOP | Aciklama |
|-----|----------|
| `code-assist` | TDD-tabanli kod implementasyonu (Explore → Plan → Code → Commit) |
| `pdd` (Prompt-Driven Development) | Kaba fikri detayli tasarim dokumenine donusturme |
| `code-task-generator` | Gereksinimleri yonetilebilir kod gorevlerine bolme |
| `codebase-summary` | Kapsamli kod tabani analizi ve dokumantasyon |
| `eval` | Strands Evals SDK ile otomatik degerlendirme |

### 14.3 SOP Formati

```markdown
---
name: skill-adi
description: Skill'in ne yaptigi
---

# SOP Adi

## Overview
Bu SOP ne yapar ve ne zaman kullanilir.

## Parameters
- **param1** (required): Aciklama
- **param2** (optional, default: "deger"): Aciklama

## Steps

### 1. Adim Adi
Adimin amacinin aciklamasi.

**Constraints:**
- You MUST [gereksinim]
- You SHOULD [oneri]
- You MAY [opsiyonel]
```

### 14.4 Entegrasyon Yontemleri

| Yontem | Kullanim |
|--------|---------|
| MCP Server | `strands-agents-sops mcp` |
| Anthropic Skills | `strands-agents-sops skills --output-dir ./skills` |
| Cursor Commands | `strands-agents-sops commands --type cursor` |
| Python SDK | `from strands_agents_sops import code_assist` |

---

## 15. A2A (AGENT-TO-AGENT) ILETISIMI

```python
from strands.agent.a2a_agent import A2AAgent

# Uzak agent'a baglan
remote_agent = A2AAgent(
    endpoint="https://agent.example.com",
    name="Uzak Uzman",
    description="Uzak uzman agent",
    timeout=300
)

# Swarm/Graph icinde yerel agent gibi kullan
swarm = Swarm(nodes=[local_agent, remote_agent])
result = swarm("Bu gorevi birlikte tamamlayin")
```

---

## 16. CIFT YONLU STREAMING (Deneysel)

```python
from strands.experimental.bidi import BidiAgent
from strands.experimental.bidi.models import BidiNovaSonicModel
from strands.experimental.bidi.io import BidiAudioIO, BidiTextIO

model = BidiNovaSonicModel(
    provider_config={
        "audio": {"input_rate": 16000, "output_rate": 16000, "voice": "matthew"},
        "turn_detection": {"endpointingSensitivity": "MEDIUM"}
    }
)

agent = BidiAgent(model=model, tools=[...])
audio_io = BidiAudioIO()
text_io = BidiTextIO()

await agent.run(
    inputs=[audio_io.input()],
    outputs=[audio_io.output(), text_io.output()]
)
```

**Desteklenen Modeller:**
- Amazon Nova Sonic (v1, v2)
- Google Gemini Live
- OpenAI Realtime API

---

## 17. GOZLEMLENEBILIRLIK (Observability)

### 17.1 OpenTelemetry Entegrasyonu

```python
agent = Agent(
    trace_attributes={
        "service.name": "my-agent",
        "deployment.environment": "production",
    }
)
```

Otomatik olarak olusturulan span'lar:
- Event loop donguleri
- Tool calistirmalari
- Model cagirilari
- Graph node calistirmalari

### 17.2 EventLoopMetrics

```python
result = agent("Merhaba")
metrics = result.metrics

# Erisilebilir metrikler:
# - input_tokens, output_tokens, total_tokens
# - model_invocation_count
# - tool_execution_count
# - total_execution_time_ms
```

### 17.3 Callback Handler

```python
def my_callback(**kwargs):
    if "data" in kwargs:
        print(kwargs["data"], end="", flush=True)  # Text chunk
    elif "current_tool_use" in kwargs:
        print(f"Tool: {kwargs['current_tool_use']}")

agent = Agent(callback_handler=my_callback)
```

---

## 18. DEVTOOLS

### 18.1 Strands Command System

GitHub issue/PR'larda `/strands` komutlari ile AI otomasyon:

| Komut | Tetiklenme | Islem |
|-------|-----------|-------|
| `/strands` (Issue) | Issue'da | Gorev inceleyen — belirsizlikleri analiz eder, soruler sorar |
| `/strands` (PR) | PR'da | Gorev uygulayici — TDD ile implementasyon |
| `/strands implement` | Issue'da | Gorev uygulayici — PR olusturur |
| `/strands release-notes` | Issue'da | Surum notlari uretici |

### 18.2 Evals Altyapisi

AWS CDK tabanli degerlendirme pipeline:
- SQS kuyrugu → Lambda calistirici → S3 sonuclar → CloudFront dashboard
- React + AWS Cloudscape dashboard (8 sayfa)
- Langfuse entegrasyonu (session izleme)

---

## 19. TIP SISTEMI

### 19.1 Temel Tipler

```python
# Girdi tipleri
AgentInput = str | list[ContentBlock] | list[InterruptResponseContent] | Messages | None

# Mesaj tipleri
Messages = list[Message]

class Message(TypedDict):
    content: list[ContentBlock]
    role: Literal["user", "assistant"]

# Icerik bloklari
class ContentBlock(TypedDict, total=False):
    text: str
    image: ImageContent
    document: DocumentContent
    video: VideoContent
    toolUse: ToolUse
    toolResult: ToolResult
    reasoningContent: ReasoningContentBlock
    citationsContent: CitationsContentBlock
    cachePoint: CachePoint

# Kullanim metrikleri
class Usage(TypedDict):
    inputTokens: int
    outputTokens: int
    totalTokens: int
```

---

## 20. HATA YONETIMI

### 20.1 Ozel Exception'lar

| Exception | Aciklama |
|-----------|----------|
| `EventLoopException` | Event loop dongusu basarisiz |
| `ContextWindowOverflowException` | Model context penceresi asildi |
| `MaxTokensReachedException` | max_tokens limitine ulasildi |
| `StructuredOutputException` | Yapilandirilmis cikti dogrulama basarisiz |
| `MCPClientInitializationError` | MCP baglanti kurulumu basarisiz |
| `ModelThrottledException` | Model rate limit |

### 20.2 Retry Stratejisi

```python
from strands.models.retry import ModelRetryStrategy

agent = Agent(
    model=BedrockModel(
        retry_strategy=ModelRetryStrategy(
            max_attempts=3,
            initial_delay=2,
            max_delay=60
        )
    )
)
```

---

## 21. DAGITIM

### 21.1 Desteklenen Platformlar

| Platform | Ozellik |
|----------|---------|
| AWS Bedrock AgentCore | Sunucusuz, agent'lar icin ozel |
| AWS Lambda | Kisa sureli etkilesimler, toplu isleme |
| AWS Fargate | Konteynerli, streaming destegi |
| AWS App Runner | Otomatik dagitim, olcekleme |
| Amazon EKS | Kubernetes, streaming destegi |
| Amazon EC2 | Maksimum kontrol |
| Docker | Konteyner bazli izolasyon |
| Terraform | Altyapi-as-Code |

### 21.2 FastAPI Streaming Ornegi

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from strands import Agent

app = FastAPI()

@app.post("/chat")
async def chat(prompt: str):
    agent = Agent(tools=[...])

    async def generate():
        async for event in agent.stream_async(prompt):
            if event.get("type") == "text":
                yield event["text"]

    return StreamingResponse(generate(), media_type="text/plain")
```

---

## 22. ORTAM DEGISKENLERI

```bash
# Model provider'lar
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
OLLAMA_HOST=http://localhost:11434

# MCP
MCP_SERVER_TIMEOUT=30

# Telemetri
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=my-agents

# Tool yapilandirmasi
BYPASS_TOOL_CONSENT=true
STRANDS_NON_INTERACTIVE=true
STRANDS_TOOL_CONSOLE_MODE=enabled
SHELL_DEFAULT_TIMEOUT=900
```

---

## 23. KAYNAKLAR

### Resmi
- Web: https://strandsagents.com
- GitHub SDK: https://github.com/strands-agents/sdk-python
- GitHub Tools: https://github.com/strands-agents/tools
- GitHub Samples: https://github.com/strands-agents/samples
- GitHub Docs: https://github.com/strands-agents/docs
- GitHub DevTools: https://github.com/strands-agents/devtools
- GitHub Agent SOP: https://github.com/strands-agents/agent-sop
- PyPI: https://pypi.org/project/strands-agents/

### AWS Blog Yazilari
- Tanitim: https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/
- 1.0 Duyurusu: https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/
- Teknik Derinlik: https://aws.amazon.com/blogs/machine-learning/strands-agents-sdk-a-technical-deep-dive-into-agent-architectures-and-observability/
- AWS Prescriptive Guidance: https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-frameworks/strands-agents.html
