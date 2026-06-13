---
id: core-loop
title: Özerk çekirdek döngü
sidebar_label: Çekirdek döngü
---

# Özerk çekirdek döngü

AETHON'un çekirdek döngüsü, bir iş birimini **alım → planlama → yürütme →
kanıtla-teslim** akışına dönüştürür: bir istek bir proje olarak tanınır, görev defterine
planlanır, sınırlı bir yürütücü tarafından tamamlanmaya doğru çalıştırılır ve kanıta
dayalı bir makbuzla geri raporlanır. Her dikiş `core_loop.*` altında kapı tutulur ve
**isteğe bağlı / varsayılan kapalıdır** — siz etkinleştirene kadar sıradan sohbete
dokunulmaz.

:::info Tasarım gereği sınırlı
Yürütücü kasıtlı olarak çitlenmiştir: bir yineleme üst sınırı, yeniden denetlenen bir
harcama tavanı ve görev başına bir deneme sınırı, özerk bir çalıştırmanın boşa dönmesini
engeller. Ayrıca ajanın düzyazısına değil, **deftere** güvenir — bir görev yalnızca
kanıtla tamamlandı olarak işaretlendiğinde tamamlanmış sayılır.
:::

## 1. Alım — bir iş birimini sınıflandır (`core_loop.intake_enabled`)

Alım açıkken, gelen bir mesaj normal tur çalışmadan önce **sohbet** veya **iş** olarak
sınıflandırılır. Sınıflandırıcı, şeffaf, yüksek eşikli bir sezgisel yöntemdir (sıcak
yolda model çağrısı yoktur) ve sohbete yatkındır — bir soru, kısa bir mesaj ya da bir
yapma/oluşturma fiilini bir proje ismiyle eşleştirmeyen her şey sohbet olarak kalır. Her
iki yönde de `core_loop.intake_work_phrases` / `intake_chat_phrases` aracılığıyla her
zaman açık bir geçersiz kılmaya sahipsiniz (ör. "bunu bir proje olarak ele al" / "sadece
bir soru").

Net bir iş birimi, normal bir sohbet turu olarak yanıtlanmak yerine, planlanmış bir proje
olarak açılır ve onaylanır. Güvenle açılmış bir projenin altında kalan her şey sıradan
işlemeye düşer; böylece sohbet asla gasp edilmez. Alım, görev defterinin ve planlayıcının
hazır olmasını gerektirir; aksi takdirde işlemsizdir (no-op).

## 2. Planlama → defter (`ask_planner`)

Planlayıcı uzman **yapılandırılmış** bir plan döndürür ve `ask_planner` bunu doğrudan
görev defterine bağımlılık sırasına göre bir proje ağacı olarak kalıcı yazar: bir ana
proje artı alt görevler; her biri bir başlık, kabul ölçütleri, bir öncelik
(`critical | high | medium | low`) ve plandaki konumlar olarak ifade edilen bağımlılıklarla.
Böylece plan, ajanın yeniden yorumlaması gereken serbest metin yerine, kullanıcının (ve
yürütücünün) inceleyebileceği görünür bir defter farkı (diff) hâline gelir. Yapılandırılmış
çıktıyı zorlayamayan bir sağlayıcı, serbest metin plana geri döner.

`core_loop.plan_approval` (varsayılan kapalı), yürütmenin, yeni planlanmış bir projeyi
kullanıcının onaylamasını beklemesi gerektiğini kaydeder; planın kendisi her zaman deftere
yazılır.

## 3. Yürütme — sınırlı `ProjectExecutor` (`core_loop.executor_enabled`)

Yürütücü açıkken ve bir proje etkinken, bir [ortam](./capabilities.md) adımı ona karşı
`ProjectExecutor`'ı çalıştırır. Her yinelemede bağımlılıkları karşılanmış en acil görevi
seçer, üzerinde bir ajan turu sürer ve yalnızca defter ilerleme gösterdiğinde ilerler.
Çalıştırma her eksende sınırlıdır:

- **`executor_max_iterations`** (varsayılan 20) — proje çalıştırması başına görev turlarına
  kesin bir üst sınır.
- **`executor_max_task_attempts`** (varsayılan 3) — bu kadar turdan sonra hiçbir ilerleme
  kaydetmeyen bir görev **düşürülür** (kalıcı olarak, böylece kuyruğu temelli terk eder —
  sayaç defterde yaşar, yeniden başlatmalardan ve yeniden çağrılardan sağ çıkar).
- **`executor_stop_on_budget`** (varsayılan açık) — token harcama tavanı görevler *arasında*
  yeniden denetlenir (tur başına kapı tek başına çok görevli bir çalıştırmayı sınırlayamaz);
  tavan aşıldığında çalıştırma durur.

Çalıştırma, yapılandırılmış bir durma nedeniyle biter: `complete`, `partial` (bazı görevler
düşürüldü), `blocked` (karşılanamaz bağımlılıklar), `cap` (yineleme sınırı) veya `budget`.

## 4. Nabız + iş-kanıtı makbuzu (`core_loop.pulse_enabled` / `receipt_enabled`)

Yürütme sırasında AETHON, işin istendiği kanala geri ilerleme **nabızları** gönderir —
her `core_loop.pulse_every_n_tasks` yeni tamamlanan görevde bir tane (varsayılan 3;
`pulse_enabled: false` ile susturulabilir).

Bir çalıştırma bittiğinde, `receipt_enabled` (varsayılan açık) dürüst bir **iş-kanıtı
makbuzu** teslim eder: tamamlanan her görev, defterin yakaladığı gerçek kanıtla listelenir
(asla yalın bir "tamamlandı" değil, asla uydurulmuş değil) ve düşürülen görevler
tamamlanmamış olarak gösterilir. Bu, ürünün "tamamlandı, işte kanıtı" karşılığıdır.

```yaml
core_loop:
  intake_enabled: false          # C1 — iş ile sohbeti sınıflandır
  executor_enabled: false        # C3 — etkin bir projede sınırlı yürütücüyü çalıştır
  executor_max_iterations: 20
  executor_max_task_attempts: 3
  executor_stop_on_budget: true
  pulse_enabled: true            # C4 — yürütme sırasında ilerleme nabızları
  pulse_every_n_tasks: 3
  receipt_enabled: true          # C4 — bir çalıştırma bittiğinde iş-kanıtı makbuzu
  plan_approval: false           # yürütmenin onay beklediğini kaydet
```

Planı üreten planlayıcı için bkz. **[Çok ajanlı uzmanlar](./multi-agent.md)**,
`manage_tasks` defteri için **[Ajan araçları](./tools.md)** ve yürütmeyi süren ortam
döngüsü için **[Yetenekler](./capabilities.md)**.
