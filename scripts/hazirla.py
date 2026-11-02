"""İçerik dosyasından (icerik/YYYY-MM-DD.json) yayın görsellerini ve planı üretir.
Çıktı: yayin/YYYY-MM-DD/*.jpg + plan.json
Kullanım: python scripts/hazirla.py [--tarih YYYY-MM-DD] (boşsa bugün ve sonrası tüm içerikler)
"""
import argparse, asyncio, datetime as dt, glob, json, os, subprocess, sys
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sablon as S
from playwright.async_api import async_playwright
from PIL import Image

UA = "TarihteBugun/1.0 (Instagram @trht.bgn; educational history account)"

def indir(url, hedef):
    if not os.path.exists(hedef):
        subprocess.run(["curl", "-sSfL", "--retry", "5", "--retry-delay", "10", "-A", UA, "-o", hedef, url], check=True)
    return hedef

ETIKET_IG, ETIKET_FB, METIN_SINIRI = 5, 3, 2200

def aciklama(icerik, g, platform):
    """Açıklama metnini her gün aynı kalıpla kurar: anlatım, soru, günün diğer olayları, kaynaklar, etiketler."""
    govde = (g["ig_metin"] if platform == "ig" else g.get("fb_metin") or g["ig_metin"]).strip()
    if "ig_etiketler" not in g:  # eski biçimli içerik dosyası: metin olduğu gibi kullanılır
        return govde
    etiketler = g["ig_etiketler"] if platform == "ig" else g.get("fb_etiketler", g["ig_etiketler"][:ETIKET_FB])
    sinir = ETIKET_IG if platform == "ig" else ETIKET_FB
    if "#" in govde: raise SystemExit(f"{g['kod']}: etiketler metnin içine değil {platform}_etiketler alanına yazılır")
    if not 1 <= len(etiketler) <= sinir or etiketler[0] != "#tarihtebugün":
        raise SystemExit(f"{g['kod']}: {platform} etiketleri 1-{sinir} adet olmalı ve #tarihtebugün ile başlamalı")
    parcalar = [govde]
    if g.get("soru"): parcalar.append(g["soru"])
    parcalar.append("Bugün başka neler oldu?\n" + "\n".join(f"{l[0]} · {l[2]}" for l in icerik["liste"]))
    kay = g["kaynaklar"].strip()
    parcalar.append(kay if kay.lower().startswith("kaynaklar") else "Kaynaklar: " + kay)
    parcalar.append(" ".join(etiketler))
    metin = "\n\n".join(parcalar)
    if len(metin) > METIN_SINIRI: raise SystemExit(f"{g['kod']}: {platform} açıklaması {len(metin)} karakter (sınır {METIN_SINIRI})")
    return metin

def baglam(icerik, g):
    C = dict(ay=icerik["ay"], gunno=icerik["gunno"], liste=[tuple(x) for x in icerik["liste"]],
             slogan1="Takvimden bir yaprak daha.", slogan2="Yarın için takipte kal.", hesap="@trht.bgn")
    C.update(g)
    C["slaytlar"] = [tuple(x) for x in g["slaytlar"]]
    if g.get("gorsel_url"):
        os.makedirs("/tmp/gorsel", exist_ok=True)
        C["gorsel"] = indir(g["gorsel_url"], f"/tmp/gorsel/{icerik['tarih']}-{g['kod']}" + os.path.splitext(g["gorsel_url"].split("?")[0])[1])
    return C

async def uret(yol):
    icerik = json.load(open(yol, encoding="utf-8"))
    tarih = icerik["tarih"]; out = f"yayin/{tarih}"
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(f"{out}/*.jpg"): os.remove(f)
    isler, plan = [], dict(tarih=tarih, onaylandi=bool(icerik.get("onaylandi")), facebook=icerik.get("facebook", True), gonderiler=[], hikayeler=[])
    for g in icerik["gonderiler"]:
        C = baglam(icerik, g); P = S.THEMES[C["tema"]]; X = S.parts(C, P)
        n = 3 + len(C["slaytlar"])
        sayfalar = [S.cover(C, P, X, n)] + [S.content(C, P, X, j + 2, n, *s) for j, s in enumerate(C["slaytlar"])] + [S.liste(C, P, X, n - 1, n), S.slogan(C, P, X, n, n)]
        adlar = []
        for j, html in enumerate(sayfalar, 1):
            ad = f"{g['kod']}-carousel-{j:02d}.jpg"; isler.append((ad, 1080, 1350, html)); adlar.append(ad)
        isler.append((f"{g['kod']}-hikaye.jpg", 1080, 1920, S.story(C, P, X)))
        plan["gonderiler"].append(dict(kod=g["kod"], gorseller=adlar, ig_metin=aciklama(icerik, g, "ig"), fb_metin=aciklama(icerik, g, "fb")))
        plan["hikayeler"].append(f"{g['kod']}-hikaye.jpg")
    # "Bugün başka neler oldu?" olaylarının her biri için ayrı hikâye karesi (carousel'leri yoktur)
    for k, l in enumerate(icerik["liste"], 1):
        h = l[3] if len(l) > 3 else None
        if not h: continue
        g = dict(kod=f"liste{k}", yil=l[0], hicri=l[1], short=l[2], kaynaklar="", slaytlar=[], tema=h.get("tema", "normal"), **{a: b for a, b in h.items() if a != "tema"})
        C = baglam(icerik, g); P = S.THEMES[C["tema"]]; X = S.parts(C, P)
        ad = f"liste{k}-hikaye.jpg"; isler.append((ad, 1080, 1920, S.story(C, P, X, liste_olayi=True))); plan["hikayeler"].append(ad)
    C0 = baglam(icerik, icerik["gonderiler"][0])
    isler.append(("son-hikaye.jpg", 1080, 1920, S.story_liste(C0)))
    plan["hikayeler"].append("son-hikaye.jpg")
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        for ad, w, h, html in isler:
            await pg.set_viewport_size({"width": w, "height": h})
            await pg.set_content(html, wait_until="load"); await pg.evaluate("document.fonts.ready")
            png = f"/tmp/{ad}.png"
            await pg.screenshot(path=png, clip={"x": 0, "y": 0, "width": w, "height": h})
            Image.open(png).convert("RGB").save(f"{out}/{ad}", "JPEG", quality=95, subsampling=0)
            print("üretildi:", f"{out}/{ad}")
        await b.close()
    json.dump(plan, open(f"{out}/plan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tarih"); a = ap.parse_args()
    bugun = dt.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")
    dosyalar = [f"icerik/{a.tarih}.json"] if a.tarih else [f for f in sorted(glob.glob("icerik/*.json")) if os.path.basename(f)[:10] >= bugun]
    for f in dosyalar: asyncio.run(uret(f))

if __name__ == "__main__":
    main()
