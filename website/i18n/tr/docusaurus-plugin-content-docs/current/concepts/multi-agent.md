---
id: multi-agent
title: Çok ajanlı uzmanlar ve devretme
sidebar_label: Çok ajanlı uzmanlar
---

# Çok ajanlı uzmanlar ve devretme (`ask_*`)

Bir ana orkestratör ajan, karmaşık işleri dört uzmana devredebilir (hepsi çalışma
zamanının modelini paylaşır):

| id | ad | odak | araçlar |
|----|------|-------|-------|
| `coder` | Coder | kod yazma, test, hata ayıklama, yeniden düzenleme (TDD) | `file_read, file_write, editor, shell, python_repl, think` |
| `researcher` | Researcher | web araştırması, belge okuma, bilgi toplama (kaynak gösterir) | `http_request, file_read, think, current_time` |
| `analyst` | Analyst | veri analizi, hesaplamalar, grafikler, raporlar | `python_repl, calculator, file_read, file_write, think` |
| `planner` | Planner | karmaşık görevleri somut adımlara bölme, önceliklendirme | `file_read, file_write, think` |

Devretme araçları: `ask_coder(task)`, `ask_researcher(query)`, `ask_analyst(data_task)`,
`ask_planner(planning_task)`. Orkestratöre, basit görevleri kendisinin halletmesi ve
karmaşık olanları devretmesi talimatı verilir.

```yaml
multi_agent:
  enabled: true
  max_handoffs: 10
  max_iterations: 10
  execution_timeout: 300.0   # seconds
  node_timeout: 120.0        # seconds
```

## Takım modları (dahili)

`ask_*` dışında, dahili olarak iki takım modu vardır:

- bir **işbirlikçi (collaborative)** mod (devretmelerle çalışan bir Strands `Swarm`;
  `multi_agent.max_handoffs / max_iterations / execution_timeout / node_timeout` ile
  yönetilir) ve
- bir **işhattı (pipeline)** modu (deterministik bir `GraphBuilder` dizisi; varsayılan
  işhattı `["planner", "researcher", "coder"]`).

:::info Yol haritası
Swarm/Graph takımı ve işhattı orkestrasyonu dahili olarak mevcuttur ancak henüz bir
komut/araç olarak çalışma zamanına bağlanmamıştır — bkz. **[Yol haritası](../project/roadmap.md)**.
:::
