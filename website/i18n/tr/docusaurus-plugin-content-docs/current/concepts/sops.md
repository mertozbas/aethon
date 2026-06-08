---
id: sops
title: SOP'lar (Standart İşletim Prosedürleri)
sidebar_label: SOP'lar
---

# SOP'lar (Standart İşletim Prosedürleri)

SOP'lar, bir eğik çizgi komutuyla çağrılan yeniden kullanılabilir iş akışlarıdır.
**Yerleşik olanlar:**

```
/code-assist        /pdd        /codebase-summary
```

(`strands-agents-sops` paketinden; `sops.builtin_sops_enabled` ile açılıp kapatılır ve
alt sistemin tamamı `sops.enabled` ile).

**Çağırma:** `/` ile başlayan bir mesaj bir SOP komutu olarak ele alınır; `/` sonrası
ilk simge SOP adı, geri kalanı ise girdinizdir. Yalnızca yüklenmiş SOP'larla eşleşir.

## Özel bir SOP yazma

Şu konumda bir Markdown dosyası oluşturun:

```
~/.aethon/workspace/sops/<name>.sop.md
```

SOP adı, `.sop.md` kaldırılmış dosya adıdır; yani `weekly-report.sop.md`,
`/weekly-report` olarak çağrılır. SOP'un açıklaması için bir `## Overview` bölümü
ayrıştırılır (ilk 200 karakter); bu, listelemelerde (panonun SOP'lar paneli ve
`/api/sops`) gösterilir. Ajanın sistem istemi, mevcut SOP eğik çizgi komutlarını adıyla
listeler. Özel SOP'lar yerleşik olanlarla birleştirilir.

```markdown
## Overview
Generate a concise weekly status report from recent commits and notes.

## Steps
1. Summarize recent activity.
2. Highlight blockers and decisions.
3. Output a Markdown report.
```

Özel SOP'ları panonun SOP'lar panelinden de oluşturabilir/düzenleyebilir/silebilirsiniz
(yerleşik olanlar silinemez).
