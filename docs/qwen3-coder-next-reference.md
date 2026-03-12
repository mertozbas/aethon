# Qwen3-Coder-Next - Kapsamli Teknik Referans Dokumani

> Son guncelleme: 2026-03-12
> Kaynak: Qwen Technical Report (arxiv 2603.00729v1), HuggingFace Model Card, Ollama Registry

---

## 1. GENEL BAKIS

Qwen3-Coder-Next, Alibaba'nin Qwen ekibinin gelistirdigi, **agentic coding** gorevleri icin ozel olarak tasarlanmis bir dil modelidir.

- **Lisans:** Apache-2.0
- **Tip:** Causal Language Model (Text Generation)
- **Odak:** Agentic software engineering, tool calling, kod uretimi
- **Thinking Mode:** SADECE non-thinking mode (think bloklari URETMEZ)

---

## 2. MIMARI DETAYLAR

### 2.1 Temel Parametreler

| Ozellik | Deger |
|---------|-------|
| Toplam Parametre | 80B (80 milyar) |
| Aktif Parametre (token basina) | 3B (3 milyar) |
| Non-Embedding Parametre | 79B |
| Hidden Dimension | 2,048 |
| Katman Sayisi | 48 |
| Attention Heads (Q) | 16 |
| Attention Heads (KV) | 2 |
| Head Dimension | 256 |
| Rotary Position Embedding | 64 boyut |
| Linear Attention Heads (V) | 32 |
| Linear Attention Heads (QK) | 16 |
| Context Length (native) | 262,144 token (256K) |
| Context Length (YaRN ile) | 1,048,576 token (1M) |
| Desteklenen Dil Sayisi | 370 programlama dili |

### 2.2 MoE (Mixture of Experts) Yapisi

| Ozellik | Deger |
|---------|-------|
| Toplam Expert Sayisi | 512 |
| Aktif Expert Sayisi (token basina) | 10 |
| Shared Expert | 1 |
| Expert Intermediate Dimension | 512 |

### 2.3 Hybrid Katman Yapisi

Model 48 katmandan olusur ve su tekrarlayan deseni kullanir:

```
12 x (3 x (Gated DeltaNet -> MoE) -> 1 x (Gated Attention -> MoE))
```

- **Gated DeltaNet:** Linear attention mekanizmasi (her blokta 3 katman)
- **Gated Attention:** Standart attention mekanizmasi (her blokta 1 katman)
- Her attention katmanindan sonra bir MoE katmani gelir
- Bu hybrid yaklasim, hesaplama verimliligini standart transformer'lara gore onemli olcude arttirir

### 2.4 Mimari (qwen3next)

- Gated DeltaNet + Gated Attention + MoE kombinasyonu
- Sparse activation: Token basina sadece 3B parametre aktif
- 10-20x daha buyuk modellere denk performans saglar

---

## 3. EGITIM METODOLOJISI

### 3.1 Asama 1: Mid-Training (On-Egitim)

**Veri Bilesimi:**

| Kaynak | Detay |
|--------|-------|
| Natural Code Data | 600B token - GitHub repo-level kod, cross-file bagimliliklar |
| Text-Code Grounding | Common Crawl iceriginin Qwen3-Coder-480B ile yeniden yazilmasi |
| GitHub PR'lar | Problem tanimi + kod baglamli + Search-and-Replace/diff formati |
| Sentetik Gorevler | ~800K dogrulanabilir yazilim muhendisligi ornegi, 9 dil |

**Veri Isleme Teknikleri:**
- Web dokumanlari yeniden formatlanir (EvalPlus'ta +8.7 puan iyilesme)
- Best-fit packing (BFP) ornekleme stratejisi: context hallucination'i onler
- Tekrarlayan segmentlere maskeleme uygulanir
- Next-token prediction + FIM objectives birlikte egitilir

### 3.2 Asama 2: Supervised Fine-Tuning (SFT)

**Veri Kaynaklari:**
1. Sirket ici ozel veri kumeleri (hizalama odakli)
2. Dogrulanmis agentic trajectory'ler (execution-validated)
3. Dokumantasyon-tabanli open-domain QA

**Dogrulama:**
- Mini-SWE-agent "kullanici simulator'u" olarak calisir
- Onerilen kodu calistirir
- Compiler ciktilari, runtime hatalari ve ortam durum degisiklikleri degerlendirilir

**Tercih Modelleme:**
- Ciftli (pairwise) degerlendirme
- Cok boyutlu kontrol listesi: olgusal dogruluk, gorev yararliligi, konusma stili

### 3.3 Asama 3: Uzman Model Egitimi

#### 3.3.1 Web Gelistirme Uzmani
- Cok asamali filtreleme
- Statik gorsel degerlendirme: VLM ile Playwright render'lanan sayfalarin incelenmesi
- Dinamik etkilesim degerlendirmesi: Browser otomasyon ile dogru sayfa davranisi dogrulama
- Rendering artefaktlari ve bozuk etkilesimlerin tespiti

#### 3.3.2 Kullanici Deneyimi Uzmani
- Farkli CLI/IDE scaffold'lari ile egitim
- **21 farkli tool chat template** icerigi:
  - JSON, XML, Python, TypeScript stilleri
  - qwen3_coder, qwen3_xml_mixed, deepseekr1, deepseekv3
  - hermes, harmony varyantlari
  - Agent-spesifik formatlar (xml_cline, xml_aone)
- Onemli bulgu: "Template cesitliligi arttikca SWE-bench Verified performansi artar"

#### 3.3.3 Tek-Tur RL Uzmani
- Yarisma programlama, kutuphane kullanimi, I/O yonetimi
- Guvenlik acigi barindiran senaryolar
- Cok dilli gorev uretimi (dile ozgu deyimler tesvik edilir)
- Unit test consensus: bagimsiz cozumler uzerinden cogunluk oyu

#### 3.3.4 Yazilim Muhendisligi Uzmani
- Cok-turlu ortam etkilesimi ile RL
- **Odul Sekillendirme Bilesenleri:**
  - Tamamlanmamis trajectory cezasi (asiri etkilesim turu icin)
  - Tur-seviyesi tool-format cezasi (kural tabanli dogrulama)
  - **Reward Hacking Engelleyici:** Hem repo linki (github.com/{repo}) hem de ag erisim anahtar kelimeleri (git, curl, wget) iceren tool cagilarini engeller
- Onemli bulgu: Ajanlar, geleneksel korumalar kaldirildiginda git komutlari ile ground-truth bilgisine eriisme yolunu otomatik kesfetti

#### 3.3.5 Uzman Damitma (Expert Distillation)
- Web Gelistirme + UX + Tek-tur RL + Yazilim Muhendisligi uzmanlari birlesik dagitim modeline konsolide edilir

### 3.4 Gorev Sentezi (Task Synthesis at Scale)

#### GitHub PR Tabanli Ortam Olusturma
- PR'lar buggy state, fix ve test patch olarak ayristirilir
- Uzmanlasmis agent, Docker ortamlarini dogrulama scriptleri ile olusturur
- Calisma(ya)n dogrulayicilarin otomatik tespiti
- Kalite-guvence agenti: belirsiz gorevleri ve uyumsuz testleri temizler
- Sonuc: **~807,693 ornek** / **52,960 depo** uzerinden

#### Sentetik Sorun Uretimi
- Model gudumlu yeniden yazma, semantik perturbasyonlar, kural tabanli donusumler ile bug enjeksiyonu
- Bug'un mevcut testleri tetikleyip tersine cevrildiginde cozuldugu dogrulanir
- Bug-tetikleyen test dosyalari haric, dogal-dil aciklamalari uretilir
- Sonuc: **~851,898 ornek** / birden fazla programlama dili

#### Altyapi: MegaFlow
- Kubernetes tabanli orkestrasyon sistemi
- Uc asamali is akislari:
  1. Agent rollout (agent + execution environment container'lari birlikte)
  2. Evaluation (ayri dogrulama container'i)
  3. Post-processing (sonuc yorumlama ve metrik cikarimi)

---

## 4. YETENEKLER VE OZELLIKLER

### 4.1 Tool Calling / Function Calling

**Format:** OpenAI-compatible function calling formati

**Tool Tanimi:**
```json
{
  "type": "function",
  "function": {
    "name": "function_adi",
    "description": "Fonksiyon aciklamasi",
    "parameters": {
      "type": "object",
      "required": ["param1"],
      "properties": {
        "param1": {
          "type": "string",
          "description": "Parametre aciklamasi",
          "enum": ["secenek1", "secenek2"]
        }
      }
    }
  }
}
```

**Yanit Formati (OpenAI-compatible):**
```json
{
  "role": "assistant",
  "tool_calls": [{
    "id": "tool_id",
    "function": {
      "name": "function_adi",
      "arguments": "{\"param1\": \"deger\"}"
    }
  }]
}
```

**Tool Sonuc Formati:**
```json
{
  "role": "tool",
  "tool_call_id": "call_id",
  "content": "{sonuc_verisi}"
}
```

**Qwen-Agent Formati (Alternatif):**
```json
{
  "role": "assistant",
  "function_call": {
    "name": "function_adi",
    "arguments": "{\"param\": \"deger\"}"
  }
}
```

**Qwen-Agent Tool Sonuc:**
```json
{
  "role": "function",
  "name": "function_adi",
  "content": "{sonuc_verisi}"
}
```

**Ozellikler:**
- Paralel tool calling destegi (tek yanitte birden fazla tool)
- Dinamik tool secimi
- Sirali tool yürutme
- Hata kurtarma (execution failure recovery)
- 21 farkli tool chat template ile egitilmis
- qwen3_coder ozel formati: string-agirlikli argumanlarda ic ice tirnak sorunlarini onler

**Format Uyum Performansi (Farkli Scaffold'larda):**

| Scaffold | Basari Orani |
|----------|-------------|
| Scaffold 1 | %98.0 |
| Scaffold 2 | %83.0 |
| Scaffold 3 | %98.0 |
| Scaffold 4 | %91.5 |
| Scaffold 5 | %93.0 |
| **Ortalama** | **%92.7** |

### 4.2 Fill-in-the-Middle (FIM) / Kod Tamamlama

**FIM Formati:**
```
<|fim_prefix|>{onceki_kod}<|fim_suffix|>{sonraki_kod}<|fim_middle|>
```

**Repository-Level FIM Formati:**
```
<|repo_name|>depo_adi
<|file_sep|>dosya_yolu1
dosya_icerigi1
<|file_sep|>dosya_yolu2
dosya_icerigi2
```

**FIM Durma Token ID'leri:** `[151659, 151661, 151662, 151663, 151664, 151643, 151645]`

**Iki Egitim Formati:**
1. **Chat-FIM:** FIM tokenlarini ChatML formati icine gomme
2. **Search-and-Replace FIM:** Diff-stili yamalar uretir (PR-stili on-egitim verisi ile guclu uyum nedeniyle daha iyi performans gosterir)

**Desteklenen FIM Benchmark'lari:**
- HumanEval-Infilling: Cesitli dillerde tek satir kod tamamlama
- CrossCodeEval (CCEval): Cok dilli tamamlama gorevleri
- CrossCodeLongEval: Uzun baglam senaryolarinda cross-file tamamlama
- RepoEval: Depo-seviyesi kod tamamlama, cok dosyali baglam

### 4.3 Chat Template (ChatML Formati)

**Standart Konusma Sablonu:**
```
<|im_start|>system
{sistem_mesaji}
<|im_end|>
<|im_start|>user
{kullanici_mesaji}
<|im_end|>
<|im_start|>assistant
{asistan_yaniti}
<|im_end|>
```

**Ozel Tokenlar:**
- `<|im_start|>` - Mesaj baslangici
- `<|im_end|>` - Mesaj sonu (ayni zamanda EOS_TOKEN)
- `<|fim_prefix|>` - FIM oncesi
- `<|fim_suffix|>` - FIM sonrasi
- `<|fim_middle|>` - FIM ortasi
- `<|repo_name|>` - Repo adi
- `<|file_sep|>` - Dosya ayirici

**Roller:**
- `system` - Baglam ve davranis ayarlari (opsiyonel)
- `user` - Kullanici istekleri (zorunlu)
- `assistant` - Model yanitlari
- `tool` - Tool sonuclari (OpenAI formati)
- `function` - Tool sonuclari (Qwen-Agent formati)

### 4.4 Desteklenen Programlama Dilleri

**370 programlama dili** desteklenir. Bunlarin arasinda:
ABAP, C, C++, C#, Python, Rust, JavaScript, TypeScript, Go, Java, Kotlin, Swift, Ruby, PHP, Perl, R, MATLAB, Scala, Haskell, Lua, Dart, SQL, Shell/Bash, PowerShell, Assembly, Fortran, COBOL, Erlang, Elixir, Clojure, F#, OCaml, Zig, Nim, Julia, Groovy, VB.NET, Objective-C, ve daha yuzlercesi.

**Detayli Benchmark Dilleri:** Python, JavaScript/TypeScript, Go, Java, C#

### 4.5 Agentic Yetenekler

- Uzun vadeli planlama (long-horizon reasoning)
- Cok-turlu ortam etkilesimi (multi-turn environment interaction)
- Hata durumundan kurtulma (execution failure recovery)
- Dinamik tool secimi ve sirali yurutme
- Depo olceginde kod anlama (256K context)
- Browser otomasyonu ve web etkilesimi
- Desktop otomasyon
- Dosya yonetimi otomasyonu

---

## 5. BENCHMARK SONUCLARI

### 5.1 SWE-Bench (Yazilim Muhendisligi)

| Benchmark | Skor |
|-----------|------|
| SWE-Bench Verified (SWE-Agent) | %70.6 |
| SWE-Bench Verified (MiniSWE-Agent) | %71.1 |
| SWE-Bench Verified (OpenHands) | %71.3 |
| SWE-Bench Multilingual | %62.8 |
| SWE-Bench Pro | %56.2 |

> Karsilastirma: Claude Sonnet 4.5 bu benchmark'ta %68.4-%76.0 arasinda.

### 5.2 Terminal-Bench 2.0

| Scaffold | Skor |
|----------|------|
| Terminus2-xml | %36.2 |
| Terminus2-json | %30.9 |
| ClaudeCode | %25.8 |
| QwenCode | %25.8 |

### 5.3 Fonksiyon-Seviye Kodlama

| Benchmark | Skor |
|-----------|------|
| EvalPlus | %86.56 |
| MultiPL-E | %88.23 |
| CRUXEval | %95.88 |
| LiveCodeBench | %58.93 |
| OJBench | 23.01 |
| Codeforces Rating | 2100 |

### 5.4 Full-Stack Gelistirme

| Benchmark | Skor |
|-----------|------|
| FullStackBench-en | %60.58 |
| FullStackBench-zh | %57.38 |
| Spider (SQL) | %83.66 |
| BIRD-SQL | %63.56 |
| Aider-Polyglot | %66.20 |

### 5.5 Genel Bilgi

| Benchmark | Skor |
|-----------|------|
| MMLU | %87.73 |
| MMLU-Redux | %91.18 |
| MMLU-Pro | %80.52 |
| GPQA | %74.49 |
| SuperGPQA | %57.45 |

### 5.6 Rekabetci Matematik

| Benchmark | Skor |
|-----------|------|
| HMMT25 Feb | %70.21 |
| HMMT25 Nov | %75.57 |
| AIME24 | %89.01 |
| AIME25 | %83.07 |

### 5.7 Ablation Calismalari

**Web Dokuman Yeniden Formatlama:**
- EvalPlus: 54.38 -> 63.09 (+8.7)
- MultiplE: 36.02 -> 48.35 (+12.3)
- CRUX-Eval: 57.13 -> 58.94 (+1.8)

**Tool Template Cesitliligi:**
- Template sayisi arttikca SWE-bench Verified performansi artar
- "Format-invariant tool-use behavior" olusturur

---

## 6. DAGITIM VE CALISTIRMA

### 6.1 Mevcut Formatlar

| Varyant | Boyut | Context | Format |
|---------|-------|---------|--------|
| Qwen3-Coder-Next (varsayilan) | 52GB | 256K | GGUF Q4_K_M |
| Qwen3-Coder-Next Q5_K_M | 56.7GB | 256K | GGUF |
| Qwen3-Coder-Next Q6_K | 65.5GB | 256K | GGUF |
| Qwen3-Coder-Next Q8_0 | 84.8GB | 256K | GGUF |
| Qwen3-Coder-Next F16 | 159GB | 256K | GGUF |
| Qwen3-Coder-Next FP8 | - | 256K | SafeTensors |

### 6.2 Bellek Gereksinimleri

| Quantization | RAM/VRAM | Uygun Donanim |
|--------------|----------|---------------|
| Q2_K | ~26-30GB | 32GB Mac Mini M4 |
| Q4_K_M / Q4_K_XL | ~46-52GB | 64GB MacBook Pro, RTX 5090 |
| Q5_K_M | ~57GB | RTX 6000 Ada / A100 80GB |
| Q6_K | ~65GB | 96GB Workstation |
| Q8_0 | ~85GB | 128GB Workstation, Dual A100 |
| F16 | ~159GB | Dual A100 80GB |

### 6.3 Ollama ile Calistirma

```bash
# Kurulum
curl -fsSL https://ollama.com/install.sh | sh

# Model indirme
ollama pull qwen3-coder-next

# Interaktif calistirma
ollama run qwen3-coder-next

# API sunucusu (varsayilan port: 11434)
ollama serve
```

**Ollama API Kullanimi:**
```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3-coder-next",
  "messages": [{"role": "user", "content": "Merhaba"}],
  "stream": false
}'
```

**Tool Calling (Ollama API):**
```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3-coder-next",
  "messages": [{"role": "user", "content": "Sayiyi karele"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "square",
      "description": "Sayinin karesini alir",
      "parameters": {
        "type": "object",
        "required": ["n"],
        "properties": {"n": {"type": "number"}}
      }
    }
  }]
}'
```

### 6.4 llama.cpp ile Calistirma

```bash
# Interaktif kullanim
./llama-cli -m ./Qwen3-Coder-Next-Q4_K_M/Qwen3-Coder-Next-00001-of-00004.gguf \
  --jinja -ngl 99 -fa on -sm row \
  --temp 1.0 --top-k 40 --top-p 0.95 --min-p 0 \
  -c 40960 -n 32768 --no-context-shift

# Sunucu modu (OpenAI-compatible API)
./llama-server -m ./model.gguf \
  --port 8001 \
  --jinja -ngl 99 -fa on
```

### 6.5 vLLM ile Calistirma

```bash
vllm serve Qwen/Qwen3-Coder-Next-FP8 \
  --tool-call-parser qwen3_coder \
  --enable-auto-tool-choice \
  --max-model-len 200000 \
  --gpu-memory-utilization 0.93 \
  --tensor-parallel-size 2
```

### 6.6 SGLang ile Calistirma

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen3-Coder-Next \
  --tool-call-parser qwen3_coder \
  --port 8000
```

### 6.7 YaRN ile Extended Context (1M token)

```bash
./llama-cli ... \
  -c 1010000 \
  --rope-scaling yarn \
  --rope-scale 4 \
  --yarn-orig-ctx 262144
```

### 6.8 OpenAI Client ile Kullanim

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",  # Ollama
    # base_url="http://localhost:8001/v1",  # llama-server
    # base_url="http://localhost:8000/v1",  # vLLM/SGLang
    api_key="not-needed"
)

# Chat completion
response = client.chat.completions.create(
    model="qwen3-coder-next",
    messages=[{"role": "user", "content": "write quicksort in python"}],
    max_tokens=65536,
    temperature=1.0,
    top_p=0.95
)

# Tool calling
tools = [{
    "type": "function",
    "function": {
        "name": "square_the_number",
        "description": "output the square of the number.",
        "parameters": {
            "type": "object",
            "required": ["input_num"],
            "properties": {
                "input_num": {
                    "type": "number",
                    "description": "input_num is a number that will be squared"
                }
            }
        }
    }
}]

response = client.chat.completions.create(
    model="qwen3-coder-next",
    messages=[{"role": "user", "content": "square the number 1024"}],
    max_tokens=65536,
    tools=tools
)
```

### 6.9 Transformers ile Kullanim

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen3-Coder-Next",
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Coder-Next")

messages = [{"role": "user", "content": "write quicksort"}]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
generated_ids = model.generate(**model_inputs, max_new_tokens=65536)
output = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)
```

---

## 7. OPTIMAL SAMPLING PARAMETRELERI

| Parametre | Onerilen Deger | Aciklama |
|-----------|---------------|----------|
| temperature | 1.0 | Yaraticilik seviyesi |
| top_p | 0.95 | Nucleus sampling |
| top_k | 40 | Top-K sampling |
| min_p | 0.01 | Minimum olasilik esigi (llama.cpp default 0.05, 0.01 onerilir) |
| repeat_penalty | 1.0 (devre disi) | Tekrar cezasi |
| max_tokens | 65536 | Maksimum cikti token |

> **ONEMLI:** Bu parametreler Qwen ekibi tarafindan onerilen degerlerdir. Farkli degerler kullanmak performansi olumsuz etkileyebilir.

---

## 8. PERFORMANS METRIKLERI (DONANIM)

### 8.1 Hiz (Token/Saniye)

| Quantization | Beklenen Hiz |
|--------------|-------------|
| Q2_K | 15-25 tok/s |
| Q4_K_XL | 25-40 tok/s |
| Q6_K | 30-45 tok/s |
| Q8_0 | 35-50 tok/s |

### 8.2 Donanim Onerileri

| Seviye | Donanim | Hiz | Fiyat |
|--------|---------|-----|-------|
| Budget | Mac Mini M4 64GB | 20-30 tok/s (Q4) | $2,000-3,000 |
| Enthusiast | RTX 5090 + 128GB DDR5 | 30-40 tok/s | $5,000-8,000 |
| Professional | Mac Studio M3 Ultra / Multi-GPU | 40-60 tok/s | $10,000-15,000 |

### 8.3 Bellek Optimizasyonu

- MoE modelleri GPU (dense layers) ve CPU RAM (sparse experts) arasinda verimli boluneblir
- Bu sayede VRAM'in tek basina izin vereceginden daha buyuk quantization'lar calistirilabilir
- OOM hatalari icin context boyutunu kucultur: `--ctx-size 32768`

---

## 9. BILINEN SINIRLAMALAR

1. **Thinking mode YOK:** `<think></think>` bloklari uretmez — derin reasoning chain'leri olusturamaz
2. **Aktif hesaplama siniri:** Frontier modellere gore daha kucuk aktif hesaplama kapasitesi
3. **Karmasik gorevlerde daha fazla tur:** Cok karmasik yazilim muhendisligi gorevlerinde daha fazla etkilesim turu gerektirebilir
4. **Frontend/UI sinirlamasi:** Frontend ve UI ile ilgili yetenekler hala gelisim alaninda
5. **Gorsel yetenek yok:** Gorsel (vision) yetenegi henuz entegre degil — gelecek calismalarda planlanmakta
6. **Genel amacli sohbet icin optimize degil:** Kodlama ve agentic gorevler icin optimize
7. **Malformed tool calls:** Uretim sirasinda parse edilemeyen tool call'lar olusabilir — production'da fallback parsing mantigi gerekli

---

## 10. AGENTIC ENTEGRASYON UYUMLULUGU

### 10.1 Dogrudan Desteklenen Platformlar
- Claude Code
- Qwen Code
- Cline
- OpenCode
- Qoder
- Kilo
- Trae

### 10.2 Tool Call Parser Ayarlari

| Platform | Parser Ayari |
|----------|-------------|
| vLLM | `--tool-call-parser qwen3_coder --enable-auto-tool-choice` |
| SGLang | `--tool-call-parser qwen3_coder` |
| Ollama | Otomatik (dahili destek) |
| llama.cpp | `--jinja` flag ile ChatML template |

### 10.3 IDE Entegrasyonlari

**Continue.dev:**
```json
{
  "models": [{
    "title": "Qwen3-Coder-Next",
    "provider": "openai",
    "model": "qwen3-coder-next",
    "apiBase": "http://localhost:11434/v1",
    "apiKey": "not-needed"
  }]
}
```

**Aider:**
```bash
aider --model openai/qwen3-coder-next \
      --openai-api-base http://localhost:11434/v1 \
      --openai-api-key not-needed
```

---

## 11. EGITIM VERISI ISTATISTIKLERI

### 11.1 Gercek Dunya Depo Ornekleri

| Dil | Ornek Sayisi | Depo Sayisi |
|-----|-------------|-------------|
| Python | 202,302 | 13,098 |
| JavaScript/TypeScript | 175,660 | - |
| Go | 121,062 | - |
| Diger diller | ~308,669 | - |
| **TOPLAM** | **807,693** | **52,960** |

### 11.2 Sentetik Gorev Veri Setleri

| Veri Seti | Ornek Sayisi |
|-----------|-------------|
| SWE-Smith | - |
| SWE-Flow | - |
| SWE-Rebench | - |
| Multi-SWE-RL | - |
| **TOPLAM** | **851,898** |

### 11.3 Tool Chat Template'leri

21 farkli template: qwen3_coder, qwen3_xml_mixed, deepseekr1, deepseekv3, hermes, harmony varyantlari, xml_cline, xml_aone ve daha fazlasi.

---

## 12. SORUN GIDERME

| Sorun | Cozum |
|-------|-------|
| Yavas inference (< 10 tok/s) | MXFP4_MOE quantization, `--no-mmap --fa on` flag'leri, context window kucultme |
| Tekrarlama/donguler | `--repeat-penalty 1.1`, sampling parametrelerini dogrulama |
| Dusuk tool-calling dogrulugu | `--tool-call-parser qwen3_coder` aktif mi kontrol, Q6_K+ quantization, llama.cpp/vLLM guncelleme |
| OOM hatalari | Context boyutunu `--ctx-size 32768` ile kucultme |
| FIM calismiyorsa | Ozel FIM tokenlari (`<\|fim_prefix\|>` vs.) dogru formatta mi kontrol |

---

## 13. KAYNAKLAR

- Teknik Rapor: https://arxiv.org/html/2603.00729v1
- HuggingFace Model: https://huggingface.co/Qwen/Qwen3-Coder-Next
- HuggingFace GGUF: https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF
- GitHub: https://github.com/QwenLM/Qwen3-Coder
- Ollama: https://ollama.com/library/qwen3-coder-next
- Blog: https://qwen.ai/blog?id=qwen3-coder-next
- Qwen Docs: https://qwen.readthedocs.io/en/latest/
- Function Calling Docs: https://qwen.readthedocs.io/en/latest/framework/function_call.html
- Unsloth GGUF: https://huggingface.co/unsloth/Qwen3-Coder-Next-GGUF
- Unsloth Guide: https://unsloth.ai/docs/models/qwen3-coder-next

---

## 14. STRANDS AGENTS ICIN NOTLAR

Bu model Strands Agents SDK ile kullanilacagi icin kritik noktalar:

1. **OpenAI-compatible API:** Ollama uzerinden `http://localhost:11434/v1` endpoint'i ile Strands'e baglanabilir
2. **Tool calling destegi:** Native tool calling - Strands tool'lari dogrudan kullanilabilir
3. **Non-thinking mode:** Agent tasarimi "act fast, think less" prensibi uzerine kurulmali
4. **Guclu yonler:** Tool orchestration, kod uretimi/duzenleme, dosya islemleri, shell komutlari
5. **Zayif yonler:** Derin soyut muhakeme, karmasik cok-adimli planlama (thinking mode olmadigi icin)
6. **Context window:** 256K token — buyuk repo'lar icin yeterli ama Strands conversation loop'larinda dikkatli yonetilmeli
7. **Sampling:** temperature=1.0, top_p=0.95, top_k=40 — bu degerler degistirilmemeli
8. **Hata yonetimi:** Malformed tool call'lar olasidır — Strands'te retry/fallback mekanizmasi onemli
