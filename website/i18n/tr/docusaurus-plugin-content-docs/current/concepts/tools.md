---
id: tools
title: Ajan araçları ve telemetri
sidebar_label: Ajan araçları
---

# Ajan araçları

Ana ajan her zaman şunlara sahiptir: `file_read, file_write, editor, shell, think,
current_time`, ayrıca `update_context` (`CONTEXT.md` dosyasını günceller), `send_message`
(etkin herhangi bir kanala iletir) ve `manage_messages` (kendi konuşmasının tur
farkındalıklı incelemesi). Görev defteri etkin olduğunda (varsayılan), ayrıca
`manage_tasks` da vardır — kalıcı görev defteri (`workspace/TASKS.json`): görevleri
`acceptance_criteria`, `evidence`, `parent_id`, `depends_on`, `priority` ve `due` ile
`create / update / complete / list` yapar. Defter, oturum sıfırlamalarından ve yeniden
başlatmalardan sağ çıkan kalıcı çalışma durumudur; çekirdek döngü planlayıcısı/yürütücüsü
onu okur ve yazar.

Koşullu olarak eklenenler:

- **bellek** — vektör bellek etkinken `manage_memory(action, content, query, category, memory_id)`.
- **devretme** — çok ajanlı sistem açıkken `ask_coder / ask_researcher / ask_analyst / ask_planner / ask_scout / ask_specialist`; ayrıca `core_loop.dynamic_specialists` etkinken `manage_specialists`.
- **zamanlayıcı** — zamanlayıcı çalışırken `schedule_task`, `list_scheduled_jobs`, `remove_scheduled_job`.
- **yetenekler** — `scraper`, `use_github`, `jsonrpc`, `notify` (`capabilities` altında yapılandırmayla kapı tutulur, varsayılan açık).
- **öğrenme** — `prompt.include_learnings` etkinken `record_learning(category, content)` (`LEARNINGS.md` dosyasına kalıcı olarak yazar).
- **macOS** (Darwin) — `macos.enabled` etkinken `use_mac`, `apple_notes`.
- **kod zekası** — `lsp.enabled` etkinken `lsp`.
- **dinamik araçlar** — `runtime_tools.enabled` etkinken `manage_tools` (yalıtılmış; onay/güvenlikle kapı tutulur).
- **bilgisayar kontrolü** — `capabilities.computer.enabled` etkinken `use_computer` (`computer` ekini gerektirir).
- **ortam (ambient)** — `ambient.enabled` etkinken `start_ambient_mode / stop_ambient_mode / get_ambient_status`.
- **MCP araçları** — MCP etkinken eklenir.

İsteğe bağlı (opt-in) araçlar ve kapıları için bkz. **[Yetenekler](./capabilities.md)**.

## Telemetri

Telemetri hook'u olayları kaydeder (en fazla `telemetry.max_history`, varsayılan 10000)
ve panoda (`/api/telemetry`, Canlı İzleyici ve Ajanlar/geçmiş görünümleri) özetleri ve
son metrikleri görünür kılar.

```yaml
telemetry:
  enabled: true
  max_history: 10000
```
