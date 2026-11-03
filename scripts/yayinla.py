"""Tarihte Bugün — günlük yayın betiği (GitHub Actions'ta çalışır).

Onaylanmış içerik: yayin/YYYY-MM-DD/plan.json + JPEG görseller.
Gizli değişkenler (GitHub Secrets): META_TOKEN (Sayfa erişim anahtarı), IG_USER_ID, FB_PAGE_ID
Kullanım:
  python scripts/yayinla.py                 # bugünün (İstanbul) planını yayınlar
  python scripts/yayinla.py --tarih 2026-11-03 --kuru   # yayınlamadan dener
"""
import argparse, datetime as dt, json, os, sys, time, urllib.parse, urllib.request, urllib.error
from zoneinfo import ZoneInfo

API = "https://graph.facebook.com/v23.0"
TZ = ZoneInfo("Europe/Istanbul")
REPO = os.environ.get("GITHUB_REPOSITORY", "mfhancerli/tarihte-bugun-yayin")
BRANCH = os.environ.get("YAYIN_DALI", "main")

def log(*a): print(dt.datetime.now(TZ).strftime("%H:%M:%S"), *a, flush=True)

SAYFA_TOKEN = None  # Facebook sayfası işlemleri için; anahtar_hazirla() doldurur

def istek(yol, veri=None, metod="POST", sayfa=False):
    tok = SAYFA_TOKEN if (sayfa and SAYFA_TOKEN) else os.environ["META_TOKEN"]
    if metod == "GET":
        url = f"{API}/{yol}?" + urllib.parse.urlencode({**(veri or {}), "access_token": tok})
        req = urllib.request.Request(url)
    else:
        body = urllib.parse.urlencode({**(veri or {}), "access_token": tok}, doseq=True).encode()
        req = urllib.request.Request(f"{API}/{yol}", data=body, method="POST")
    sunucu, kota = 0, 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            hata = e.read().decode(errors="replace")
            if e.code >= 500 and sunucu < 3:
                sunucu += 1; log("sunucu hatası, tekrar:", e.code); time.sleep(10 * sunucu); continue
            kod = hata.replace(" ", "")
            if any(f'"code":{k},' in kod for k in (4, 17, 32, 613)) and kota < 8:
                # Meta istek kotası doldu: kota kayan bir saatlik pencerede yenilenir; bekleyip yeniden dene.
                kota += 1; log(f"Meta istek kotası doldu; 5 dk bekleniyor ({kota}/8):", yol); time.sleep(300); continue
            if '"code":190' in hata.replace(" ", ""):
                raise SystemExit("Meta erişim anahtarı geçersiz ya da iptal edilmiş (kod 190). Yeni anahtar üretip "
                                 f"GitHub Secrets'taki META_TOKEN'a kaydedin. Meta'nın yanıtı: {hata}")
            raise SystemExit(f"Graph API hatası {e.code} ({yol}): {hata}")

def anahtar_hazirla(ig, page):
    """Anahtarı doğrular. Sayfa anahtarı da, kullanıcı ya da sistem kullanıcısı anahtarı da kabul edilir;
    ikinci durumda Facebook işlemleri için sayfa anahtarı otomatik alınır."""
    global SAYFA_TOKEN
    ben = istek("me", {"fields": "id,name"}, "GET")
    if ben.get("id") == page:
        SAYFA_TOKEN = os.environ["META_TOKEN"]; log("Anahtar türü: SAYFA anahtarı")
    else:
        r = istek(page, {"fields": "access_token"}, "GET")
        if not r.get("access_token"):
            raise SystemExit("Anahtar sayfaya erişemiyor: sayfa anahtarı alınamadı. Sistem kullanıcısına sayfanın atandığını kontrol edin.")
        SAYFA_TOKEN = r["access_token"]; log("Anahtar türü: KULLANICI/SİSTEM anahtarı; sayfa anahtarı otomatik alındı")
    hesap = istek(ig, {"fields": "username"}, "GET")
    istek(page, {"fields": "name"}, "GET", sayfa=True)
    return hesap.get("username")

def gorsel_url(tarih, dosya):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/yayin/{tarih}/{urllib.parse.quote(dosya)}"

def bekle_hazir(kap_id, sinir=300):
    t0 = time.time(); time.sleep(2)  # görseller çoğunlukla ilk sorguda hazırdır; seyrek sorgu kotayı korur
    while time.time() - t0 < sinir:
        d = istek(kap_id, {"fields": "status_code"}, "GET")
        s = d.get("status_code")
        if s == "FINISHED": return
        if s in ("ERROR", "EXPIRED"): raise SystemExit(f"Konteyner {kap_id} durumu: {s}")
        time.sleep(8)
    raise SystemExit(f"Konteyner {kap_id} zaman aşımı")

def ig_carousel(ig, tarih, g, kuru):
    cocuklar = []
    for f in g["gorseller"]:
        c = istek(f"{ig}/media", {"image_url": gorsel_url(tarih, f), "is_carousel_item": "true"})["id"]
        bekle_hazir(c); cocuklar.append(c); log("  IG sayfa hazır:", f)
    kap = istek(f"{ig}/media", {"media_type": "CAROUSEL", "children": ",".join(cocuklar), "caption": g["ig_metin"]})["id"]
    bekle_hazir(kap)
    if kuru: log("  [KURU] IG carousel hazır, yayınlanmadı:", g["kod"]); return
    m = istek(f"{ig}/media_publish", {"creation_id": kap}); log("  IG carousel yayınlandı:", g["kod"], m.get("id"))

def ig_hikaye(ig, tarih, f, kuru):
    kap = istek(f"{ig}/media", {"image_url": gorsel_url(tarih, f), "media_type": "STORIES"})["id"]
    bekle_hazir(kap)
    if kuru: log("  [KURU] IG hikâye hazır:", f); return
    m = istek(f"{ig}/media_publish", {"creation_id": kap}); log("  IG hikâye yayınlandı:", f, m.get("id"))

def fb_hikaye(page, tarih, f, kuru):
    # Facebook sayfa hikâyesi: fotoğraf yayınlanmamış olarak yüklenir, sonra photo_stories ile hikâye yapılır.
    pid = istek(f"{page}/photos", {"url": gorsel_url(tarih, f), "published": "false"}, sayfa=True)["id"]
    if kuru:
        istek(pid, {"method": "delete"}, sayfa=True); log("  [KURU] FB hikâye yüklemesi çalışıyor (deneme fotoğrafı silindi):", f); return
    m = istek(f"{page}/photo_stories", {"photo_id": pid}, sayfa=True); log("  FB hikâye yayınlandı:", f, m.get("post_id"))

def fb_coklu(page, tarih, g, kuru):
    if kuru:
        # Görünmeyen (yayınlanmamış) bir fotoğraf yükleyip hemen silerek sayfa iznini dener.
        pid = istek(f"{page}/photos", {"url": gorsel_url(tarih, g["gorseller"][0]), "published": "false"}, sayfa=True)["id"]
        istek(pid, {"method": "delete"}, sayfa=True)
        log("  [KURU] FB sayfa yükleme izni çalışıyor (deneme fotoğrafı silindi):", g["kod"]); return
    ids = [istek(f"{page}/photos", {"url": gorsel_url(tarih, f), "published": "false"}, sayfa=True)["id"] for f in g["gorseller"]]
    veri = {"message": g.get("fb_metin") or g["ig_metin"]}
    for i, pid in enumerate(ids): veri[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    m = istek(f"{page}/feed", veri, sayfa=True); log("  FB gönderisi yayınlandı:", g["kod"], m.get("id"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarih"); ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--bekle", action="store_true", help="İstanbul saatiyle 00:00'a kadar bekle")
    ap.add_argument("--kontrol", action="store_true", help="Yayın yapmadan anahtarı ve yarının planını denetle")
    ap.add_argument("--sadece", default="", help="Yalnızca bu adımlar (virgülle): ig-carousel, fb, hikaye, fb-hikaye")
    a = ap.parse_args()
    simdi = dt.datetime.now(TZ)
    if a.kontrol:
        kullanici = anahtar_hazirla(os.environ["IG_USER_ID"], os.environ["FB_PAGE_ID"])
        log("Anahtar çalışıyor. Instagram hesabı:", kullanici)
        yarin = (simdi + dt.timedelta(days=1)).strftime("%Y-%m-%d"); yol = f"yayin/{yarin}/plan.json"
        if not os.path.exists(yol):
            print(f"::warning::Yarın ({yarin}) için plan yok; bu gece yayın yapılmayacak.", flush=True)
        elif not json.load(open(yol, encoding="utf-8")).get("onaylandi"):
            print(f"::warning::Yarının ({yarin}) planı henüz onaylanmadı; onaylanmazsa bu gece yayın yapılmayacak.", flush=True)
        else:
            log("Yarının planı hazır ve onaylı:", yarin)
        return
    if a.bekle:
        hedef = (simdi + dt.timedelta(hours=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if simdi.hour == 23 and (hedef - simdi).total_seconds() < 3600:
            log("00:00 bekleniyor:", int((hedef - simdi).total_seconds()), "sn"); time.sleep(max(0, (hedef - simdi).total_seconds()))
        simdi = dt.datetime.now(TZ)
    tarih = a.tarih or simdi.strftime("%Y-%m-%d")
    yol = f"yayin/{tarih}/plan.json"
    if not os.path.exists(yol):
        log("Bu gün için onaylanmış plan yok:", yol, "— yayın yapılmadı."); return
    plan = json.load(open(yol, encoding="utf-8"))
    if not plan.get("onaylandi") and not a.kuru:
        print("::warning::Plan onaylı değil (onaylandi=false); yayın yapılmadı.", flush=True); return
    ig, page = os.environ["IG_USER_ID"], os.environ["FB_PAGE_ID"]
    log("Hesap:", anahtar_hazirla(ig, page), "| tarih:", tarih, "| kuru:" if a.kuru else "")
    adim = set(x.strip() for x in a.sadece.split(",") if x.strip()) or {"ig-carousel", "fb", "hikaye", "fb-hikaye"}
    # Çift yayın koruması: daha önce yayınlanmış carousel ve Facebook gönderileri atlanır; günün herhangi bir
    # gönderisi önceden yayınlanmışsa (önceki bir çalıştırma) hikâyeler de tekrar paylaşılmaz.
    ig_var, fb_var = set(), set()
    if not a.kuru:
        ig_son = [m.get("caption") or "" for m in istek(f"{ig}/media", {"fields": "caption", "limit": "25"}, "GET").get("data", [])]
        fb_son = [m.get("message") or "" for m in istek(f"{page}/posts", {"fields": "message", "limit": "25"}, "GET", sayfa=True).get("data", [])]
        for g in plan["gonderiler"]:
            if any(c.startswith(g["ig_metin"][:80]) for c in ig_son): ig_var.add(g["kod"])
            if any(m.startswith((g.get("fb_metin") or g["ig_metin"])[:80]) for m in fb_son): fb_var.add(g["kod"])
        if (ig_var or fb_var) and not a.sadece:
            log("Bu günün bazı gönderileri zaten yayınlanmış:", sorted(ig_var | fb_var), "— hikâyeler tekrar paylaşılmayacak.")
            adim.discard("hikaye"); adim.discard("fb-hikaye")
    hatalar = []
    def dene(ad, fn, *args):
        # Bir adım hata verirse kaydedip sıradakine geçer; diğer gönderiler etkilenmez.
        try:
            fn(*args)
        except SystemExit as e:
            hatalar.append(f"{ad}: {e}"); print(f"::error::{ad}: {e}", flush=True)
    for g in plan["gonderiler"]:
        log("Gönderi:", g["kod"])
        if "ig-carousel" in adim:
            if g["kod"] in ig_var: log("  IG carousel zaten yayınlanmış, atlandı:", g["kod"])
            else: dene(f"Instagram {g['kod']}", ig_carousel, ig, tarih, g, a.kuru)
        if "fb" in adim and plan.get("facebook", True):
            if g["kod"] in fb_var: log("  FB gönderisi zaten yayınlanmış, atlandı:", g["kod"])
            else: dene(f"Facebook {g['kod']}", fb_coklu, page, tarih, g, a.kuru)
        time.sleep(5)
    for f in plan.get("hikayeler", []):
        if "hikaye" in adim: dene(f"Instagram hikâye {f}", ig_hikaye, ig, tarih, f, a.kuru)
        if "fb-hikaye" in adim and plan.get("facebook", True): dene(f"Facebook hikâye {f}", fb_hikaye, page, tarih, f, a.kuru)
        time.sleep(3)
    if hatalar:
        raise SystemExit(f"{len(hatalar)} adım başarısız oldu: " + " | ".join(hatalar))
    log("Bitti.")

if __name__ == "__main__":
    main()
