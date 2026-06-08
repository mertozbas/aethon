---
id: workspace
title: Çalışma alanı dosyaları (SOUL / TOOLS / CONTEXT)
sidebar_label: Çalışma alanı dosyaları
---

# Çalışma alanı dosyaları (SOUL / TOOLS / CONTEXT)

`aethon start` çalıştırıldığında AETHON, `~/.aethon/workspace` konumundaki çalışma
alanının var olduğundan emin olur ve üç Markdown dosyası oluşturur (her biri yalnızca
henüz mevcut değilse yazılır — yaptığınız düzenlemeler korunur):

- **`SOUL.md`** — asistanın kişiliği/sistem kimliği. Bölümler: **Identity** (pragmatik
  ve doğrudan ol; hatalarını üstlen; bilmediğinde söyle), **Communication** (İngilizce
  ve Türkçe konuşur, kullanıcının dilinde yanıt verir; kısa ve odaklı yanıtlar; Markdown
  biçimlendirmesi), **Decision Making** (basit görevleri doğrudan yap; karmaşık görevler
  için bir plan öner; en basit yaklaşımı seç).
- **`TOOLS.md`** — tercihleriniz ve yetenekleriniz. Bölümler: **Code Standards**
  (Python 3.10+, tip ipuçları, f-string'ler, asyncio + OOP, gereksiz yorum yok, gerçek
  veriye karşı test), **Expert Delegation** (`ask_coder`, `ask_researcher`,
  `ask_analyst`, `ask_planner`), **Memory** (`manage_memory` ile kaydet; kategoriler
  preferences/projects/decisions/learnings; asla gizli bilgi saklama), **Context**
  (`update_context` ile `CONTEXT.md` dosyasını güncel tut).
- **`CONTEXT.md`** — canlı çalışma durumu; **Active Project**, **Recent Decisions** ve
  **Notes** için boş yer tutucularla başlatılır.

Ayrıca `<workspace>/sops` dizinini, oturumlar dizinini, günlükler dizinini ve (bellek
etkinse) bellek veritabanının üst dizinini oluşturur.

:::tip
Bu dosyalar asistanın davranışının **ta kendisidir**. Kişiliğini değiştirmek için
`SOUL.md` dosyasını, standartlarınızı belirlemek için `TOOLS.md` dosyasını düzenleyin
ve `update_context` aracı aracılığıyla `CONTEXT.md` dosyasını güncel tutmasına izin
verin.
:::
