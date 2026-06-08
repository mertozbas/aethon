---
id: model-backends
title: Model Arka Uçları
sidebar_label: Model Arka Uçları
---

# Model Arka Uçları

AETHON, sağlayıcıyı `~/.aethon/config.yaml` içindeki `model.provider` değerinden
seçer. Varsayılan **`openai`**'dir (`gpt-4o`). Kurulum sihirbazı (`aethon init`),
varsayılanı **openai** olan bir sağlayıcı menüsü sunar: **openai / anthropic / ollama**.

## OpenAI (varsayılan)

Varsayılan sağlayıcıyı çalıştırmanın iki yolu vardır — resmi OpenAI API'si ya da
**OpenAI uyumlu herhangi bir uç nokta**.

**Resmi OpenAI API'si** — bir API anahtarı sağlayın:

```yaml
model:
  provider: openai
  model_id: gpt-4o
  api_key: ${OPENAI_API_KEY}   # ortamdan çözümlenir
```

**OpenAI uyumlu herhangi bir uç nokta** — bunun yerine `host`'u bir base URL'ye
yönlendirin. Bu, **vLLM**, **LM Studio** veya **LocalAI** gibi yerel sunucularla ya
da OpenAI API'sini konuşan herhangi bir servisle çalışır. Birçok yerel sunucu gerçek
bir anahtara ihtiyaç duymaz (gerekiyorsa boş olmayan herhangi bir yer tutucu kullanın):

```yaml
model:
  provider: openai
  model_id: gpt-4o            # uç noktanızın sunduğu model id'sini kullanın
  host: http://localhost:8000/v1   # OpenAI uyumlu base URL'niz
  api_key: ${OPENAI_API_KEY}       # yerel sunucular için bir yer tutucu olabilir
```

:::tip
`aethon init` sihirbazı OpenAI API anahtarınızı ve isteğe bağlı olarak OpenAI uyumlu
bir base URL'yi sorar — bu yüzden bunu genellikle elle düzenlemezsiniz.
:::

## Paketle gelen `codex-proxy` aracılığıyla ChatGPT Pro

Depo, `codex-proxy/` altında **codex-proxy**'yi içerir — **ChatGPT / Codex Desktop**
aboneliğinizi **OpenAI uyumlu** bir `/v1/chat/completions` uç noktası olarak sunan
bir ters proxy. AETHON'u ona yönlendirerek asistanı, OpenAI API kredisi harcamak
yerine **ChatGPT Pro** planınızdan çalıştırın.

:::info Gizli bilgileriniz yerel kalır
codex-proxy, hesap jetonlarını `codex-proxy/data/` altında saklar; bu dizin
**gitignore'lanmıştır** ve asla commit edilmez. İçerilen kopya **yalnızca kaynak**
olarak gelir (`node_modules/` yok, `data/` yok); `npm install` bağımlılıkları geri
yükler ve ilk giriş `data/`'yı oluşturur.
:::

**1. codex-proxy'yi çalıştırın** (Node 18+ gerektirir):

```bash
cd codex-proxy
npm install
cp .env.example .env          # isteğe bağlı: OAuth girişini atlamak için bir CODEX_JWT_TOKEN yapıştırın
npm run dev                   # http://127.0.0.1:8080 üzerinde OpenAI uyumlu bir API sunar
```

İlk çalıştırmada, proxy üzerinden giriş yapın (OAuth ya da `.env` içinde
`CODEX_JWT_TOKEN` ayarlayın). Port, `.env` içindeki `PORT`'tur (varsayılan `8080`).

**2. AETHON'u ona yönlendirin** (`~/.aethon/config.yaml`):

```yaml
model:
  provider: openai
  model_id: gpt-5.5                 # ChatGPT planınızın sunduğu bir model (ör. gpt-5.5 / gpt-5.4)
  host: http://127.0.0.1:8080/v1    # codex-proxy uç noktası
  api_key: ${CODEX_PROXY_KEY}       # proxy'nin API anahtarı (codex-proxy/.env içinde ayarlayın)
  max_tokens: 8192
```

AETHON'u kullanırken codex-proxy'yi çalışır halde tutun — kapalıysa, sohbet
istekleri bağlantı hatasıyla başarısız olur. codex-proxy, burada kolaylık için
içerilen üçüncü taraf bir araçtır; tam yapılandırma, hesap yönetimi ve Docker
kurulumu için kendi `README.md`'sine bakın.

## Anthropic API

Ekstrayı kurun (`pip install "aethon-ai[anthropic]"`), ardından:

```yaml
model:
  provider: anthropic
  model_id: claude-opus-4-8
  api_key: ${ANTHROPIC_API_KEY}   # ortamdan çözümlenir
```

:::note
`temperature`, `claude-opus-4-8` istekleri için kasıtlı olarak atlanmıştır.
:::

## Ollama (tamamen yerel)

Ekstrayı kurun (`pip install "aethon-ai[ollama]"`), ardından:

```yaml
model:
  provider: ollama
  model_id: llama3.1
  host: http://localhost:11434
```

API anahtarı yok, bulut çağrısı yok — her şey kendi makinenizde çalışır.

## Diğer sağlayıcılar (bedrock / gemini / litellm / mistral)

Bunlar da model fabrikası tarafından desteklenir. `provider`'ı buna göre ayarlayın
ve her arka ucun ihtiyaç duyduğu parametreleri sağlayın — örneğin **Bedrock** tarzı
arka uçlar için `region` (varsayılan `us-west-2`) ve **Gemini / Mistral** için
`api_key`. `litellm` sağlayıcısı yalnızca `model_id` kullanır (kimlik bilgilerini
`model.api_key` ile değil, LiteLLM'in kendi ortam değişkenleriyle yapılandırın).
`model.extra` yalnızca `ollama` sağlayıcısı için iletilir (onun örnekleme
`options`'ına birleştirilir); bedrock/gemini/litellm/mistral `extra`'yı yok sayar.

Bu arka uçların her biri kendi SDK'sinin kurulu olmasını gerektirir (hiçbiri
aethon'un çekirdeğiyle ya da bir ekstrayla paketlenmez): `pip install boto3`
(Bedrock), `google-genai` (Gemini), `litellm` (LiteLLM) ya da `mistralai` (Mistral).

```yaml
model:
  provider: bedrock
  model_id: anthropic.claude-3-5-sonnet
  region: us-west-2
```

## Sihirbaza bırakın: `aethon init`

```bash
aethon init
```

Sihirbaz bir sağlayıcı menüsünde (**openai / anthropic / ollama**) ilerler.
**openai** için bir API anahtarı ve isteğe bağlı olarak OpenAI uyumlu bir base URL
sorar; ayrıca mesajlaşma botlarını yapılandırır ve bellek için Ollama gömmelerini
kullandığınızda Ollama'yı kurmayı ve gömme modelini indirmeyi önerir. Sihirbaz
sağlayıcıyı, modeli ve belleği ayarlar ve yapılandırma dosyasını sizin için
**yazar**. Bir yol seçmek için `--config / -c` (varsayılan `~/.aethon/config.yaml`)
ve mevcut bir yapılandırmayı sormadan üzerine yazmak için `--force` kullanın.
Yapılandırdıktan sonra her şeyi şununla doğrulayın:

```bash
aethon doctor
```

`aethon doctor` sağlayıcınızı/modelinizi yazdırır, bir sağlayıcı erişilebilirlik
kontrolü çalıştırır ve belleğin etkin olup olmadığını ve hangi gömme sağlayıcısını
kullandığını gösterir.
