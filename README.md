# Graficast

## Kurulum

1. Poetry kurulumu:
```bash
pip install poetry
```

2. Bağımlılıkları yükle:
```bash
poetry install
```

3. Sanal ortamı aktifleştir:
```bash
poetry shell
```

4. Uygulamayı çalıştır:
```bash
uvicorn main:app --reload
``` 

## Olası Hatalar
    
* Google Photos API token sürelerinin dolması - 6 ay kadar periyotlar ile sıfırlanıyor.
    * Çözüm: Graficast servisinin `get_token_manual.py` scriptini lokalde çalıştırıp konsoldaki base64 veriyi MongoDB üzerinde ilgili alana kaydederiz.


* MongoDB ve Render.com anlaşmazlığı - Süre bilgim yok, Render.com belli periyotolar ile erişilebilir ip'lerini değiştiriyor.
  * Çözüm: Render.com - Graficast servisinde Connect butonundan 'Outbound IP Addresses' kısmına gelip ilgili ip adreslerini MongoDB 'IP Access List' alanına ekleriz.
