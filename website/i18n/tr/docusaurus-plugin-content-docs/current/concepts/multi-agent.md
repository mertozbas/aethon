---
id: multi-agent
title: Çok ajanlı uzmanlar ve devretme
sidebar_label: Çok ajanlı uzmanlar
---

# Çok ajanlı uzmanlar ve devretme (`ask_*`)

Bir ana orkestratör ajan, karmaşık işleri yerleşik uzmanlarına devredebilir (hepsi
çalışma zamanının modelini paylaşır):

| id | ad | odak | araçlar |
|----|------|-------|-------|
| `coder` | Coder | kod yazma, test, hata ayıklama, yeniden düzenleme (TDD) | `file_read, file_write, editor, shell, python_repl, think` |
| `researcher` | Researcher | web araştırması, belge okuma, bilgi toplama (kaynak gösterir) | `http_request, file_read, think, current_time` |
| `analyst` | Analyst | veri analizi, hesaplamalar, grafikler, raporlar | `python_repl, calculator, file_read, file_write, think` |
| `planner` | Planner | karmaşık görevleri somut, önceliklendirilmiş adımlara bölme | `file_read, file_write, think` |
| `scout` | Scout | "çok oku, az döndür" araştırması: kaynakları okur/arar, yalnızca özlü bir sonuç döndürür | `file_read, shell, think` |

Devretme araçları: `ask_coder(task)`, `ask_researcher(query)`, `ask_analyst(data_task)`,
`ask_planner(planning_task)`, `ask_scout(query)` ve genel
`ask_specialist(specialist_name, task)` (yerleşik veya özel, herhangi bir uzmana adıyla
ulaşır). Orkestratöre, basit görevleri kendisinin halletmesi ve karmaşık olanları
devretmesi talimatı verilir.

`ask_scout`, "çok oku, az döndür" aracıdır: scout, gösterdiğiniz kaynakları okur/arar ve
yalnızca özlü bir sonuç döndürür; ham dökümleri ana ajanın bağlamından uzak tutar (yalıtım
tavsiye niteliğindedir — scout'un kendi görev tanımına uymasına dayanır, araç çıktısı üst
sınırı yapısal güvence olarak kalır).

Görev defteri bağlı olduğunda (Faz 10), `ask_planner` artık serbest metin döndürmez:
yapılandırılmış bir planı, bağımlılık sırasına göre bir proje ağacı olarak deftere kalıcı
yazar (ana proje + kabul ölçütleri, öncelikler ve bağımlılıklar içeren alt görevler) ve bir
özet döndürür; sağlayıcı yapılandırılmış çıktı üretemediğinde geri dönüş olarak serbest
metin plan kullanılır.

## Özel uzmanlar (isteğe bağlı)

**`core_loop.dynamic_specialists`** açıkken (varsayılan **kapalı**), ajan kendi
uzmanlarını tanımlayabilir. `manage_specialists(action, name, system_prompt, tools)`,
özel uzmanları oluşturur, listeler ve kaldırır; bunlar oturumlar arasında
`workspace/specialists/*.json` konumuna kalıcı yazılır; ardından `ask_specialist(name,
task)`, bunların herhangi birine adıyla devreder.

- Bir uzmanın araçları, sabit bir izin listesinden (`file_read`, `file_write`, `editor`,
  `shell`, `think`, `current_time`, `python_repl`, `http_request`, `calculator`) gelmek
  zorundadır; bu, hem oluşturma sırasında hem de diskten yüklenirken uygulanır — elle
  düzenlenmiş bir JSON dosyası, izinli olmayan bir aracı içeri kaçıramaz.
- **Güçlü** araçlar (`shell`, `python_repl`, `file_write`, `editor`, `http_request`)
  yalnızca `core_loop.allow_powerful_specialists` açıkken verilir; aksi takdirde yalnızca
  salt okunur/saf hesaplama alt kümesi kullanılabilir.
- Bir uzman oluşturmak onay kapılıdır ve özel uzmanlar, yerleşiklerle aynı güvenlik,
  yalıtım ortamı ve hook'ları devralır.

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
