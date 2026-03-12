# AETHON — Faz 3: Multi-Agent + SOP

> Hedef: Uzman agent takimi ve yapilandirilmis is akislari calisiyor.
> Tahmini Sure: 1-2 Hafta
> Oncelik: P1 (Onemli)
> Onkosul: Faz 1 tamamlanmis (Faz 2 istege bagli)

---

## 1. Faz Ozeti

Faz 3, AETHON'un OpenClaw'a karsi EN BUYUK avantajini insa eder:

```
                    Kullanici mesaji
                          │
                          ▼
                  ┌───────────────┐
                  │  ORCHESTRATOR │
                  │  (Ana Agent)  │
                  └───────┬───────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
     ┌──────▼──────┐ ┌───▼─────┐ ┌────▼──────┐
     │   Kodcu    │ │Arastirma│ │  Analist  │
     │   Agent   │ │  Agent  │ │  Agent    │
     └───────────┘ └─────────┘ └───────────┘
            │             │             │
            ▼             ▼             ▼
     Agent-as-Tool   Swarm Mode    Graph Mode

                    +

            ┌──────────────────┐
            │   SOP RUNNER     │
            │                  │
            │  /code-assist    │
            │  /pdd            │
            │  /morning-brief  │
            └──────────────────┘
```

---

## 2. Implementasyon Sirasi

### Adim 3.1: SpecialistFactory

**Dosya:** `aethon/agent/specialists.py`

```python
from strands import Agent
from strands.models import OllamaModel
from strands_tools import file_read, file_write, editor, shell, python_repl
from strands_tools import http_request, calculator, think, current_time

SPECIALIST_CONFIGS = {
    "coder": {
        "name": "Kodcu",
        "system_prompt": (
            "Sen bir yazilim gelistirme uzmanisin.\n"
            "Gorevlerin: kod yazma, test etme, debug etme, refactoring.\n"
            "TDD prensiplerini takip et: once test yaz, sonra implement et.\n"
            "Kisa, temiz, yorumsuz kod yaz.\n"
            "Isini bitirdiginde sonucu acikca bildir."
        ),
        "tools": [file_read, file_write, editor, shell, python_repl, think],
    },
    "researcher": {
        "name": "Arastirmaci",
        "system_prompt": (
            "Sen bir arastirma uzmanisin.\n"
            "Gorevlerin: web arastirmasi, dokumantasyon okuma, bilgi toplama.\n"
            "Kaynaklari belirt. Ozet ve analizle sun.\n"
            "Net, dogrulanabilir bilgiler ver."
        ),
        "tools": [http_request, file_read, think, current_time],
    },
    "analyst": {
        "name": "Analist",
        "system_prompt": (
            "Sen bir veri analisti ve raporlamacisin.\n"
            "Gorevlerin: veri analizi, hesaplama, grafik olusturma, rapor yazma.\n"
            "Net, olculebilir sonuclar sun.\n"
            "Sayisal verileri tablo formatinda goster."
        ),
        "tools": [python_repl, calculator, file_read, file_write, think],
    },
    "planner": {
        "name": "Planlayici",
        "system_prompt": (
            "Sen bir proje planlayicisisin.\n"
            "Gorevlerin: karmasik gorevleri adim adim bolme, onceliklendirme.\n"
            "Her adimi net, somut ve uygulanabilir yap.\n"
            "Bagimliliklar ve riskleri belirt."
        ),
        "tools": [file_read, file_write, think],
    },
}


class SpecialistFactory:
    """Uzman agent'lar olustur."""

    def __init__(self, model: OllamaModel):
        self.model = model
        self._cache: dict[str, Agent] = {}

    def get(self, specialist_name: str) -> Agent:
        """Uzman agent al veya olustur."""
        if specialist_name not in self._cache:
            config = SPECIALIST_CONFIGS.get(specialist_name)
            if not config:
                raise ValueError(f"Bilinmeyen uzman: {specialist_name}")

            self._cache[specialist_name] = Agent(
                model=self.model,
                system_prompt=config["system_prompt"],
                tools=config["tools"],
                name=config["name"],
                agent_id=specialist_name,
            )
        return self._cache[specialist_name]

    def get_all(self) -> dict[str, Agent]:
        """Tum uzman agent'lari al."""
        return {name: self.get(name) for name in SPECIALIST_CONFIGS}
```

---

### Adim 3.2: Delegate Tool'lari

**Dosya:** `aethon/tools/delegate.py`

```python
from strands import tool

# Global referans — runtime tarafindan set edilecek
_specialist_factory = None

def set_specialist_factory(factory):
    global _specialist_factory
    _specialist_factory = factory


@tool
def ask_coder(task: str) -> str:
    """Kodlama gorevini kodcu uzmanina devret.
    Kodcu; kod yazma, test etme, debug, refactoring yapar.

    Args:
        task: Kodlama gorevi aciklamasi
    """
    if not _specialist_factory:
        return "Hata: Specialist factory baslatilmamis."
    coder = _specialist_factory.get("coder")
    result = coder(task)
    try:
        content = result.message["content"]
        texts = [block["text"] for block in content if "text" in block]
        return "\n".join(texts) if texts else str(result)
    except (KeyError, TypeError):
        return str(result)


@tool
def ask_researcher(query: str) -> str:
    """Arastirma gorevini arastirmaci uzmanina devret.
    Arastirmaci; web arastirmasi, dokumantasyon okuma, bilgi toplama yapar.

    Args:
        query: Arastirilacak konu veya soru
    """
    if not _specialist_factory:
        return "Hata: Specialist factory baslatilmamis."
    researcher = _specialist_factory.get("researcher")
    result = researcher(query)
    try:
        content = result.message["content"]
        texts = [block["text"] for block in content if "text" in block]
        return "\n".join(texts) if texts else str(result)
    except (KeyError, TypeError):
        return str(result)


@tool
def ask_analyst(data_task: str) -> str:
    """Veri analizi gorevini analist uzmanina devret.
    Analist; veri analizi, hesaplama, grafik olusturma, rapor yazma yapar.

    Args:
        data_task: Analiz gorevi aciklamasi
    """
    if not _specialist_factory:
        return "Hata: Specialist factory baslatilmamis."
    analyst = _specialist_factory.get("analyst")
    result = analyst(data_task)
    try:
        content = result.message["content"]
        texts = [block["text"] for block in content if "text" in block]
        return "\n".join(texts) if texts else str(result)
    except (KeyError, TypeError):
        return str(result)


@tool
def ask_planner(planning_task: str) -> str:
    """Planlama gorevini planlayici uzmanina devret.
    Planlayici; karmasik gorevleri adim adim boler, onceliklendirir.

    Args:
        planning_task: Planlanacak gorev aciklamasi
    """
    if not _specialist_factory:
        return "Hata: Specialist factory baslatilmamis."
    planner = _specialist_factory.get("planner")
    result = planner(planning_task)
    try:
        content = result.message["content"]
        texts = [block["text"] for block in content if "text" in block]
        return "\n".join(texts) if texts else str(result)
    except (KeyError, TypeError):
        return str(result)
```

---

### Adim 3.3: Orchestrator Agent Guncellemesi

**Guncelleme:** `aethon/agent/runtime.py`

```python
# AethonRuntime._get_tools — Faz 3 guncellemesi

def _get_tools(self) -> list:
    """Faz 3 tool listesi — delegate tool'lar dahil."""
    from strands_tools import file_read, file_write, editor, shell, think, current_time
    from aethon.tools.delegate import ask_coder, ask_researcher, ask_analyst, ask_planner

    base_tools = [file_read, file_write, editor, shell, think, current_time]
    delegate_tools = [ask_coder, ask_researcher, ask_analyst, ask_planner]

    if self.config.multi_agent.enabled:
        return base_tools + delegate_tools
    return base_tools
```

**Orchestrator System Prompt'a ekleme:**
```
## Agent Delegasyonu
Karmasik gorevlerde uzman agent'lari kullan:
- ask_coder: Kodlama gorevleri (kod yazma, test, debug)
- ask_researcher: Arastirma gorevleri (web arama, dokumantasyon)
- ask_analyst: Analiz gorevleri (veri analizi, rapor)
- ask_planner: Planlama gorevleri (gorev bolme, onceliklendirme)

Basit gorevleri kendin yap. Karmasik gorevlerde uygun uzmana devret.
```

---

### Adim 3.4: TeamOrchestrator — Swarm Modu

**Dosya:** `aethon/agent/teams.py`

```python
from strands import Agent
from strands.multiagent import Swarm, GraphBuilder
from aethon.agent.specialists import SpecialistFactory

class TeamOrchestrator:
    """Multi-agent takim yonetimi."""

    def __init__(self, specialist_factory: SpecialistFactory, orchestrator: Agent):
        self.factory = specialist_factory
        self.orchestrator = orchestrator

    def collaborative_task(self, task: str) -> str:
        """Swarm modu — agent'lar birbirine gorev devreder."""
        specialists = self.factory.get_all()
        all_agents = [self.orchestrator] + list(specialists.values())

        swarm = Swarm(
            nodes=all_agents,
            entry_point=self.orchestrator,
            max_handoffs=10,
            max_iterations=10,
            execution_timeout=300.0,  # 5 dakika
            node_timeout=120.0,       # Agent basina 2 dakika
        )

        result = swarm(task)

        # Sonucu cikar
        try:
            return result.final_response
        except AttributeError:
            return str(result)

    def pipeline_task(self, task: str, pipeline: list[str] | None = None) -> str:
        """Graph modu — belirli sirada calisir."""
        if pipeline is None:
            pipeline = ["planner", "researcher", "coder"]

        builder = GraphBuilder()

        # Node'lari ekle
        nodes = {}
        for spec_name in pipeline:
            agent = self.factory.get(spec_name)
            node = builder.add_node(agent, spec_name)
            nodes[spec_name] = node

        # Edge'leri ekle (sirayla)
        for i in range(len(pipeline) - 1):
            builder.add_edge(nodes[pipeline[i]], nodes[pipeline[i + 1]])

        # Entry point
        builder.set_entry_point(pipeline[0])
        builder.set_execution_timeout(300.0)
        builder.set_node_timeout(120.0)

        graph = builder.build()
        result = graph(task)

        try:
            return result.final_response
        except AttributeError:
            return str(result)
```

---

### Adim 3.5: SOPRunner

**Dosya:** `aethon/sops/runner.py`

```python
from pathlib import Path
from strands import Agent

class SOPRunner:
    """SOP yukleme ve calistirma."""

    def __init__(self, sop_directories: list[str]):
        self.sop_dirs = [Path(d).expanduser() for d in sop_directories]
        self._sops: dict[str, str] = {}
        self._load_sops()

    def _load_sops(self):
        """Tum SOP dosyalarini yukle."""
        # 1. Dahili SOP'lar (strands-agents-sops)
        try:
            from strands_agents_sops import code_assist, pdd, codebase_summary
            self._sops["code-assist"] = code_assist
            self._sops["pdd"] = pdd
            self._sops["codebase-summary"] = codebase_summary
        except ImportError:
            pass

        # 2. Ozel SOP'lar (workspace/sops/)
        for sop_dir in self.sop_dirs:
            if not sop_dir.exists():
                continue
            for sop_file in sop_dir.glob("*.sop.md"):
                name = sop_file.stem.removesuffix(".sop")
                # Ozel SOP'lar dahili SOP'lari override eder
                self._sops[name] = sop_file.read_text(encoding="utf-8")

    def list_sops(self) -> list[dict]:
        """Kullanilabilir SOP'lari listele."""
        result = []
        for name, content in self._sops.items():
            # Overview section'i cikar (varsa)
            import re
            match = re.search(r"## Overview\s*\n(.*?)(?=\n##|\n#|\Z)", content, re.DOTALL)
            description = match.group(1).strip() if match else ""
            result.append({"name": name, "description": description[:200]})
        return result

    def get_sop(self, name: str) -> str | None:
        """SOP icerigini al."""
        return self._sops.get(name)

    def run_sop(self, name: str, agent: Agent, user_input: str = "") -> str:
        """SOP'u agent uzerinde calistir."""
        sop_content = self.get_sop(name)
        if not sop_content:
            return f"SOP bulunamadi: {name}"

        # SOP'u XML wrapper ile sar (strands-agents-sops formati)
        prompt = (
            f'<agent-sop name="{name}">\n'
            f'<content>\n{sop_content}\n</content>\n'
            f'<user-input>\n{user_input}\n</user-input>\n'
            f'</agent-sop>'
        )

        # Agent'a SOP'u calistir
        result = agent(prompt)

        try:
            content = result.message["content"]
            texts = [block["text"] for block in content if "text" in block]
            return "\n".join(texts) if texts else str(result)
        except (KeyError, TypeError):
            return str(result)

    def is_sop_command(self, text: str) -> tuple[bool, str, str]:
        """Mesajin SOP komutu olup olmadigini kontrol et.

        Returns:
            (is_sop, sop_name, user_input)
        """
        text = text.strip()
        if not text.startswith("/"):
            return False, "", ""

        parts = text.split(maxsplit=1)
        sop_name = parts[0][1:]  # "/" kaldir
        user_input = parts[1] if len(parts) > 1 else ""

        if sop_name in self._sops:
            return True, sop_name, user_input

        return False, "", ""
```

**Runtime Entegrasyonu:**

```python
# AethonRuntime.process — Faz 3 guncellemesi

def process(self, message: InboundMessage, session_id: str) -> str:
    # SOP komutu mu?
    is_sop, sop_name, sop_input = self.sop_runner.is_sop_command(message.text)

    if is_sop:
        agent = self.get_or_create_agent(session_id)
        return self.sop_runner.run_sop(sop_name, agent, sop_input)

    # Normal mesaj
    agent = self.get_or_create_agent(session_id)
    result = agent(message.text)
    return self._extract_text(result)
```

---

### Adim 3.6: ApprovalHookProvider (Interrupt)

**Dosya:** `aethon/agent/hooks/approval.py`

```python
from strands import Interrupt
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent

class ApprovalHookProvider(HookProvider):
    """Tehlikeli tool'lar icin Interrupt ile kullanici onayi."""

    def __init__(self, requires_approval: list[str] | None = None):
        self.requires_approval = set(requires_approval or ["shell", "file_write", "send_message"])

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self.check_approval)

    def check_approval(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use["name"]

        if tool_name in self.requires_approval:
            tool_input = event.tool_use.get("input", {})
            tool_use_id = event.tool_use.get("toolUseId", "unknown")

            interrupt = Interrupt(
                id=f"approval-{tool_name}-{tool_use_id}",
                name=f"{tool_name}_approval",
                reason={
                    "tool": tool_name,
                    "parameters": tool_input,
                    "message": f"'{tool_name}' calistirilmak isteniyor. Onayla?",
                },
            )
            # Not: Interrupt'in nasil raise edilecegi Strands SDK versiyonuna bagli
            # InterruptException yoksa, event uzerinden set edilir
            # Bkz: strands/interrupt.py
```

---

### Adim 3.7: Yapilandirilmis Cikti (Pydantic)

**Kullanim Ornegi:**

```python
from pydantic import BaseModel
from strands import Agent

class TaskPlan(BaseModel):
    title: str
    steps: list[str]
    estimated_hours: float
    risks: list[str]

# Agent'i yapilandirilmis cikti ile cagir
result = agent(
    "Bu projeyi planla",
    structured_output_model=TaskPlan,
)

# result.output → TaskPlan instance
plan = result.output
print(plan.title)
print(plan.steps)
```

**Runtime Entegrasyonu:**

```python
# Bazi SOP'lar yapilandirilmis cikti gerektirebilir
# SOP icerisinde structured_output_model parametresi belirtilir
# SOPRunner bu parametreyi agent cagrisina aktarir
```

---

## 3. Kullanim Senaryolari

### Senaryo 1: Agent-as-Tool (Varsayilan)

```
Kullanici: "login sayfasinin CSS'ini duzelt"

Orchestrator:
  → Karar: Bu bir kodlama gorevi
  → ask_coder("login sayfasinin CSS'ini duzelt") cagirir

Kodcu Agent:
  → file_read ile login.css okur
  → Sorunu tespit eder
  → editor ile duzeltir
  → Sonucu dondurur

Orchestrator:
  → Kullaniciya sonucu iletir
```

### Senaryo 2: Swarm (Isbirligi)

```
Kullanici: "Bu projeyi analiz et ve performans raporu hazirla"

Orchestrator → Planlayici:
  → Gorev adimlarini belirle
  → Planlayici → Kodcu'ya handoff

Kodcu:
  → Profiling calistir
  → Kodcu → Analist'e handoff

Analist:
  → Profiling sonuclarini analiz et
  → Rapor hazirla
  → Son yanit

Kullaniciya rapor iletilir
```

### Senaryo 3: Graph (Pipeline)

```
Kullanici: "Yeni API endpoint implement et"

Graph Pipeline: Planlama → Arastirma → Kodlama

1. Planlayici: Endpoint tasarimini planlar
2. Arastirmaci: Mevcut kodu ve API standartlarini inceler
3. Kodcu: Implement eder

Son yanit kullaniciya iletilir
```

### Senaryo 4: SOP Tetikleme

```
Kullanici: "/code-assist task=fix-memory-leak"

SOPRunner:
  → code-assist.sop.md yuklenir
  → Agent'a SOP talimatlari enjekte edilir
  → Explore → Plan → Code → Commit adimlari sirayla calisir
  → Sonuc kullaniciya iletilir
```

---

## 4. Dogrulama Kontrol Listesi

```
[ ] ask_coder tool'u calisiyor — kodlama gorevi kodcu agent'a devrediliyor
[ ] ask_researcher tool'u calisiyor
[ ] ask_analyst tool'u calisiyor
[ ] ask_planner tool'u calisiyor
[ ] Orchestrator basit gorevleri kendisi yapiyor
[ ] Orchestrator karmasik gorevleri uygun uzmana devrediyor
[ ] Swarm modunda agent'lar birbirine handoff yapiyor
[ ] Graph modunda pipeline sirayla calisiyor
[ ] /code-assist komutu SOP tetikliyor
[ ] /pdd komutu SOP tetikliyor
[ ] Ozel SOP dosyasi yazilip ~/.aethon/workspace/sops/ dizinine konulabiliyor
[ ] Ozel SOP /komut ile tetiklenebiliyor
[ ] Yapilandirilmis cikti (Pydantic modeli) calisiyor
[ ] ApprovalHookProvider tehlikeli tool'larda kullanici onayi istiyor
```
