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

def istek(yol, veri=None, metod="POST"):
    tok = os.environ["META_TOKEN"]
    if metod == "GET":
        url = f"{API}/{yol}?" + urllib.parse.urlencode({**(veri or {}), "access_token": tok})
        req = urllib.request.Request(url)
    else:
        body = urllib.parse.urlencode({**(veri or {}), "access_token": tok}, doseq=True).encode()
        req = urllib.request.Request(f"{API}/{yol}", data=body, method="POST")
    for deneme in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            hata = e.read().decode(errors="replace")
            if e.code >= 500 and deneme < 3:
                log("sunucu hatası, tekrar:", e.code); time.sleep(10 * (deneme + 1)); continue
            raise SystemExit(f"Graph API hatası {e.code} ({yol}): {hata}")

def gorsel_url(tarih, dosya):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/yayin/{tarih}/{urllib.parse.quote(dosya)}"

def bekle_hazir(kap_id, sinir=300):
    t0 = time.time()
    while time.time() - t0 < sinir:
        d = istek(kap_id, {"fields": "status_code"}, "GET")
        s = d.get("status_code")
        if s == "FINISHED": return
        if s in ("ERROR", "EXPIRED"): raise SystemExit(f"Konteyner {kap_id} durumu: {s}")
        time.sleep(4)
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

def fb_coklu(page, tarih, g, kuru):
    if kuru:
        # Görünmeyen (yayınlanmamış) bir fotoğraf yükleyip hemen silerek sayfa iznini dener.
        pid = istek(f"{page}/photos", {"url": gorsel_url(tarih, g["gorseller"][0]), "published": "false"})["id"]
        istek(pid, {"method": "delete"})
        log("  [KURU] FB sayfa yükleme izni çalışıyor (deneme fotoğrafı silindi):", g["kod"]); return
    ids = [istek(f"{page}/photos", {"url": gorsel_url(tarih, f), "published": "false"})["id"] for f in g["gorseller"]]
    veri = {"message": g.get("fb_metin") or g["ig_metin"]}
    for i, pid in enumerate(ids): veri[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    m = istek(f"{page}/feed", veri); log("  FB gönderisi yayınlandı:", g["kod"], m.get("id"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarih"); ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--bekle", action="store_true", help="İstanbul saatiyle 00:00'a kadar bekle")
    a = ap.parse_args()
    simdi = dt.datetime.now(TZ)
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
    ben = istek("me", {"fields": "id"}, "GET")
    log("Anahtar türü:", "SAYFA anahtarı (doğru)" if ben.get("id") == page else "KULLANICI anahtarı — Facebook yayını için sayfa anahtarı gerekir")
    hesap = istek(ig, {"fields": "username"}, "GET"); log("Hesap:", hesap.get("username"), "| tarih:", tarih, "| kuru:" if a.kuru else "")
    hatalar = []
    def dene(ad, fn, *args):
        # Bir adım hata verirse kaydedip sıradakine geçer; diğer gönderiler etkilenmez.
        try:
            fn(*args)
        except SystemExit as e:
            hatalar.append(f"{ad}: {e}"); print(f"::error::{ad}: {e}", flush=True)
    for g in plan["gonderiler"]:
        log("Gönderi:", g["kod"])
        dene(f"Instagram {g['kod']}", ig_carousel, ig, tarih, g, a.kuru)
        if plan.get("facebook", True): dene(f"Facebook {g['kod']}", fb_coklu, page, tarih, g, a.kuru)
        time.sleep(5)
    for f in plan.get("hikayeler", []):
        dene(f"Hikâye {f}", ig_hikaye, ig, tarih, f, a.kuru); time.sleep(3)
    if hatalar:
        raise SystemExit(f"{len(hatalar)} adım başarısız oldu: " + " | ".join(hatalar))
    log("Bitti.")

if __name__ == "__main__":
    main()
