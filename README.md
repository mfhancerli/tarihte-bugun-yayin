# Tarihte Bugün — yayın otomasyonu (@trht.bgn)

Bu depo, onaylanmış "Tarihte Bugün" içeriklerini her gece 00:00'da (İstanbul) Instagram'a ve Facebook sayfasına yayınlar.

1. **İçerik:** Onaylanan günün içeriği `icerik/YYYY-AA-GG.json` dosyasına yazılır. `"onaylandi": true` olmayan içerik asla yayınlanmaz.
2. **Görseller (`hazirla.yml`):** İçerik dosyası depoya gelince Takvim Yaprağı v2 şablonuyla carousel ve hikâye görselleri üretilir ve `yayin/YYYY-AA-GG/` klasörüne kaydedilir.
3. **Yayın (`yayin.yml`):** Her gece 23:40'ta çalışır, 00:00'ı bekler; önce carousel'leri (sayfa sırasıyla), sonra hikâyeleri yayınlar.

Gizli değişkenler (Settings → Secrets and variables → Actions): `META_TOKEN`, `IG_USER_ID`, `FB_PAGE_ID`.
Elle deneme: Actions → "Günlük yayın" → Run workflow ("Kuru çalıştırma" işaretliyken hiçbir şey yayınlanmaz).
