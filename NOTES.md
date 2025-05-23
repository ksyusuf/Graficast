# Proje Notları

## Dağıtım ve Render.com Ayarları
- Proje bağımlılıkları `pyproject.toml` dosyasında tutuluyor, klasik `requirements.txt` kullanılmıyor.
- Render.com veya başka bir sunucuda dağıtım yaparken build komutunu şu şekilde ayarlamalısın:
  - **Build Command:** `pip install poetry && poetry install --no-root`
  - **Start Command:** `poetry run uvicorn main:app --host 0.0.0.0 --port $PORT`
- `--no-root` parametresi, projeyi paket olarak kurmadan sadece bağımlılıkları yükler. (Eğer paket olarak kurmak isterseniz, pyproject.toml'daki `packages` alanı doğru olmalı.)

## Versiyonlama Sistemi (SemVer)
- Versiyonlama tamamen GitHub Actions ile otomatik yapılır.
- Semantic Versioning (SemVer) standartları kullanılır: `MAJOR.MINOR.PATCH`
  - **MAJOR:** Geriye uyumsuz API değişiklikleri (örn: API yapısı değişti)
  - **MINOR:** Geriye uyumlu yeni özellikler (örn: Yeni endpoint eklendi)
  - **PATCH:** Geriye uyumlu hata düzeltmeleri (örn: Bug fix)
- Versiyon artışı commit mesajına göre belirlenir:
  - **Major:** Commit mesajında `BREAKING CHANGE` varsa
  - **Minor:** Commit mesajında `feat:` varsa
  - **Patch:** Diğer tüm commitler
- PR main'e merge edildiğinde workflow otomatik çalışır, versiyonu artırır ve yeni bir git tag oluşturur.
- Versiyon bilgisi `core/version.py` dosyasında tutulur ve health endpoint'inden görülebilir.

## Commit Kuralları
- **Major:** `BREAKING CHANGE: ...`
- **Minor:** `feat: ...`
- **Patch:** `fix: ...` veya diğer commitler

## Önemli Notlar
- Tüm bağımlılıklar sadece `pyproject.toml`'da tutulmalı, gereksiz yere `requirements.txt` oluşturulmamalı.
- Yerel geliştirme için `poetry install` ve `poetry shell` komutlarını kullan.
- Dağıtımda eksik paket hatası alırsan, ilgili paketi `pyproject.toml`'a ekle.
- Versiyonlama ve dağıtım süreçleri tamamen otomatiktir, elle müdahale gerektirmez.
- **ÖNEMLİ:** Her push işleminden sonra `git pull` yapmalısın çünkü GitHub Actions versiyonu güncellediğinde, yerel dosyaların da güncellenmesi gerekir.

# Google Photos Servisi Notları

## Token ve Kimlik Bilgileri Yönetimi

### Token Yönetimi
- `token.pickle` dosyası güvenlik nedeniyle GitHub'a gönderilmiyor
- Dağıtım ortamında (örn. Render.com) token şu şekilde saklanıyor:
  1. `token.pickle` dosyası base64 formatına çevriliyor
  2. Base64 değeri `TOKEN_BASE64` environment variable'ı olarak saklanıyor
  3. Uygulama başlatıldığında, Settings sınıfı bu değeri decode edip geçici bir `token.pickle` dosyası oluşturuyor
  4. Bu sayede dağıtım ortamında Google yetkilendirme penceresi açılmadan token kullanılabiliyor

### Kimlik Bilgileri Yönetimi
- `credentials.json` dosyası yerine `GOOGLE_CREDENTIALS_JSON` environment variable'ı kullanılıyor
- Bu değer Settings sınıfı tarafından parse edilip kullanılıyor
- Geçici `credentials.json` dosyası oluşturulup işlem sonunda siliniyor

## Dağıtım Ortamı Ayarları

### Render.com'da Yapılması Gerekenler
1. Environment Variables bölümüne eklenmesi gereken değişkenler:
   - `TOKEN_BASE64`: `token.pickle` dosyasının base64 formatındaki hali
   - `GOOGLE_CREDENTIALS_JSON`: `credentials.json` içeriği

### Base64 Dönüşümü
```bash
# Windows PowerShell'de token.pickle'ı base64'e çevirme
python -c "import base64; print(base64.b64encode(open('token.pickle', 'rb').read()).decode())"
```

### Token Edinme ve Base64 Dönüşümü
Token oluşturma işlemi `get_token_manual.py` dosyası üzerinden yapılmaktadır. Bu script:
1. Google Photos API için gerekli yetkilendirmeyi yapar
2. Token'ı oluşturur
3. Base64 formatına çevirir

Script'i çalıştırmak için:
```bash
python get_token_manual.py
```

## Güvenlik Önlemleri
- Hassas bilgiler (token, credentials) environment variable'larda saklanıyor
- Geçici dosyalar işlem sonunda temizleniyor
- Token yenileme işlemi otomatik yapılıyor

## Geliştirme Ortamı
- Lokal geliştirme ortamında `token.pickle` ve `credentials.json` dosyaları kullanılabilir
- Settings sınıfı her iki durumu da destekliyor
- Token yenileme işlemi otomatik yapılıyor

## Performans İyileştirmeleri
- Aynı bilgilerle resim üretilirse, mevcut media_item_id kullanılıyor
- Gereksiz yüklemeler önleniyor
- Albüm sıralaması yeni-eski şeklinde yapılıyor

## Hata Yönetimi
- Google Photos API hataları özel exception sınıfı ile yönetiliyor
- Token ve credentials hataları detaylı loglanıyor
- Kullanıcı dostu hata mesajları döndürülüyor 