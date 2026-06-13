---
id: troubleshooting
title: Sorun Giderme
sidebar_label: Sorun Giderme
---

# Sorun Giderme

## Sağlayıcı hazır değil

`aethon start` bir kullanılabilirlik denetimi çalıştırır; bu denetim başarısız olursa `Provider not ready:
<msg>` ve bir ipucu yazdırır. Yeniden yapılandırmak için `aethon init`, tanılama için `aethon doctor`
çalıştırın. API sağlayıcıları (OpenAI, Anthropic, …) için, `api_key` değerinin (veya onun `${ENV_VAR}`
karşılığının) gerçekten ayarlandığını doğrulayın — eksik ortam değişkenlerinin boş bir dizgeye
çözümlendiğini unutmayın. **OpenAI uyumlu bir uç nokta** kullanıyorsanız, `model.host` değerinin doğru
temel URL olduğunu, sunucunun çalıştığını ve yapılandırdığınız `model_id` değerini sunduğunu iki kez
kontrol edin. **Ollama** için, daemon'un `model.host` adresinde (varsayılan `http://localhost:11434`)
çalıştığından ve modelin çekildiğinden (pull) emin olun.

## Port zaten kullanımda (18790)

Başka bir işlem WebChat portunu tutuyor. `channels.webchat.port` değerini değiştirin veya diğer işlemi
durdurun. Docker'da `18790:18790` eşlemesini ayarlayın.

## Bellek için Ollama gerekiyor

Varsayılan `ollama` gömme (embedding) sağlayıcısıyla, vektör belleği `nomic-embed-text` ile çalışan bir
Ollama gerektirir:

```bash
ollama pull nomic-embed-text
```

Başlangıçta, model eksikse `Memory: nomic-embed-text not found — ollama pull nomic-embed-text` mesajını,
Ollama'ya erişilemiyorsa `Memory: Ollama connection error` mesajını görürsünüz.
Alternatif olarak `embedding_provider: openai` (bir `embedding_api_key` ile) sağlayıcısına geçin veya
belleği devre dışı bırakın.

## Docker sağlayıcınıza erişemiyor

`model.host`, host üzerindeki bir hizmete işaret ediyorsa (ör. yerel bir OpenAI uyumlu sunucu veya
Ollama), container içinden `http://host.docker.internal:<port>` kullanın ve `host.docker.internal`
adının çözümlendiğinden emin olun — Compose,
`extra_hosts: host.docker.internal:host-gateway` ayarını yapar; düz `docker run` için
`--add-host host.docker.internal:host-gateway` ekleyin. Resmi OpenAI API için ise yalnızca
`OPENAI_API_KEY` değerini container'a geçirin.

## Mesajlaşma botu başlamadı

Eksik kütüphaneler bir uyarı, eksik token'lar ise bir `ValueError` günlüğe kaydeder — gateway çalışmaya
devam eder. Kanalın `enabled: true` olduğunu, token ortam değişkeninin ayarlandığını ve
(Discord) MESSAGE CONTENT intent'inin / (Slack) Socket Mode + olay aboneliklerinin yapılandırıldığını
kontrol edin.

## "AETHON is already running (pid N)"

İkinci bir `aethon start` bu mesajla hemen çıkar. `~/.aethon/aethon.pid` üzerindeki tek-örnek (single-instance)
`flock` kilidi, iki gateway'in aynı kanallar için yarışmasını önler (ör. ikinci bir poller'ı reddeden
Telegram'ın uzun yoklayıcısı). Önce diğer örneği durdurun veya — kilidi serbest bırakmadan çöktüyse —
kilidi tutan canlı bir işlem olmadığından emin olun.

## Bir kanal çöktü ama geri kalanı çalışmaya devam etti

Kanal adaptörleri bir gözetmen (supervisor) altında çalışır: çöken bir adaptör, traceback'iyle birlikte
günlüğe kaydedilir ve **geri çekilmeyle (backoff) yeniden başlatılır**; bu sırada diğer kanallar hizmet
vermeye devam eder; tüm gateway çökmez. Kalıcı olarak başarısız olan bir kanal yalnızca kendisini
bozar. Yeniden başlatma izini günlükte kontrol edin.

## Yeniden başlatmadan sonra zamanlanmış işler / hatırlatıcılar

Çalışma zamanında eklenen zamanlamalar `workspace/SCHEDULE.json` dosyasına kalıcı olarak yazılır;
böylece cron işleri ve tek seferlik `run_at` hatırlatıcıları ("yarın 15:30'da bana hatırlat") bir yeniden
başlatmayı atlatır ve asistan zamanlanmış anda kapalı olsa bile tetiklenir.

## Asistan bir hatada sessizleşti

Bir model veya çalışma zamanı hatasında, her kanal artık sessizleşmek yerine `aethon doctor`'a işaret
eden kısa, yerelleştirilmiş bir hata yanıtı gönderir. Bir oturum içindeki turlar, oturum başına bir kilit
(per-session lock) ile sıraya konur; böylece yavaş veya başarısız bir tur, aynı oturumdaki bir sonraki
mesajla araya giremez — ikinci mesaj, birincisi bitene kadar bekler.
