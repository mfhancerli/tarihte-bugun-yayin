"""Takvim Yaprağı v2 — sayfa HTML üreticileri (hikâye, kapak, içerik, liste, slogan)."""
import html
e = html.escape
def up(s): return s.replace("i", "İ").replace("ı", "I").upper()

THEMES = {
    "normal": dict(paper="#F1EADC", band="#B5321F", bandtxt="#F6EEE2", hole="#F1EADC", num="#1C1A16", month="#B5321F",
                   ink="#1C1A16", mute="#5F574B", ph="#E6DDCB", phline="#CDC2AE", rule="#B5321F", hair="#CFC5B3"),
    "huzunlu": dict(paper="#1D1F24", band="#AAB4BE", bandtxt="#1D1F24", hole="#1D1F24", num="#ECE8DF", month="#AAB4BE",
                    ink="#ECE8DF", mute="#A6A9AF", ph="#262A31", phline="#3B404A", rule="#AAB4BE", hair="#3B404A"),
}
PF = "font-family: 'Playfair Display', serif"
WS = "font-family: 'Work Sans', sans-serif"
SAFE_BOT = 1670

def page(w, h, bg, inner):
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>html,body{{margin:0;padding:0}}'
            f'*{{-webkit-font-smoothing:antialiased}}</style></head><body>'
            f'<div style="position:relative;width:{w}px;height:{h}px;overflow:hidden;background:{bg}">{inner}</div></body></html>')

def parts(C, P):
    def band(h, holes_y, txt_y=None, txt_size=44):
        s = (f'<div style="position:absolute;left:0;top:0;width:1080px;height:{h}px;background:{P["band"]}"></div>'
             f'<div style="position:absolute;left:116px;top:{holes_y}px;width:40px;height:40px;border-radius:20px;background:{P["hole"]}"></div>'
             f'<div style="position:absolute;right:116px;top:{holes_y}px;width:40px;height:40px;border-radius:20px;background:{P["hole"]}"></div>')
        if txt_y is not None:
            s += (f'<div style="position:absolute;left:0;right:0;top:{txt_y}px;text-align:center;{WS};font-weight:700;'
                  f'font-size:{txt_size}px;letter-spacing:0.32em;color:{P["bandtxt"]}">TARİHTE BUGÜN</div>')
        return s
    def hook_fs(t, big): return big if len(t) <= 40 else big - 6 if len(t) <= 60 else big - 12
    def short_fs(t, base): return base if len(t) <= 120 else base - 2 if len(t) <= 220 else base - 4
    def yil_html(size):
        s = f'<div style="{PF};font-weight:900;font-size:{size}px;line-height:1;color:{P["num"]}">{C["yil"]}</div>'
        if C.get("hicri"):
            s += f'<div style="{WS};font-weight:600;font-size:{max(22, size // 3)}px;letter-spacing:0.12em;color:{P["mute"]};margin-top:8px">HİCRİ {C["hicri"]}</div>'
        return s
    def date_inline(numsize, monsize, yilsize):
        return (f'<div style="flex:none;display:flex;align-items:center;gap:46px">'
                f'<div style="{PF};font-weight:900;font-size:{numsize}px;line-height:0.8;color:{P["num"]}">{C["gunno"]}</div>'
                f'<div style="flex:1;display:flex;flex-direction:column;gap:12px">'
                f'<div style="{WS};font-weight:700;font-size:{monsize}px;line-height:1;color:{P["month"]}">{up(C["ay"])}</div>'
                f'<div style="height:6px;background:{P["rule"]}"></div><div>{yil_html(yilsize)}</div></div></div>')
    def tipo(minh, big=150):
        if C.get("gorsel"):
            import base64, mimetypes
            mt = mimetypes.guess_type(C["gorsel"])[0] or "image/jpeg"
            b64 = base64.b64encode(open(C["gorsel"], "rb").read()).decode()
            return (f'<div style="flex:1 1 0;min-height:{minh}px;display:flex;flex-direction:column;gap:10px">'
                    f'<div style="flex:1 1 0;min-height:0;border:2px solid {P["phline"]};box-sizing:border-box;overflow:hidden;background:{P["ph"]}">'
                    f'<img src="data:{mt};base64,{b64}" style="width:100%;height:100%;object-fit:cover;object-position:{C.get("gorsel_odak", "center")};display:block"></div>'
                    f'<div style="text-align:right;{WS};font-size:22px;color:{P["mute"]}">Görsel: {e(C.get("gorsel_kaynak", ""))}</div></div>')
        # Görsel yerine tipografik alan (lisanslı görsel bulunamadığında)
        bsz = big if len(C["tipo_buyuk"]) <= 4 else int(big * 0.55)
        return (f'<div style="flex:1 1 0;min-height:{minh}px;background:{P["ph"]};border:2px solid {P["phline"]};box-sizing:border-box;'
                f'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:24px;text-align:center">'
                f'<div style="{PF};font-weight:900;font-size:{bsz}px;line-height:0.95;color:{P["month"]}">{e(C["tipo_buyuk"])}</div>'
                f'<div style="{WS};font-weight:700;font-size:34px;letter-spacing:0.3em;color:{P["ink"]}">{e(C["tipo_alt"])}</div>'
                f'<div style="{WS};font-size:24px;line-height:1.4;color:{P["mute"]};max-width:760px;margin-top:6px">{e(C["tipo_not"])}</div></div>')
    def text_block(hook, short, hbig, sbase, gap=16):
        return (f'<div style="flex:none;display:flex;flex-direction:column;gap:{gap}px">'
                f'<h1 style="margin:0;{PF};font-weight:800;font-size:{hook_fs(hook, hbig)}px;line-height:1.06;color:{P["ink"]}">{e(hook)}</h1>'
                f'<p style="margin:0;{WS};font-size:{short_fs(short, sbase)}px;line-height:1.4;color:{P["mute"]}">{e(short)}</p></div>')
    def mini():
        hic = (f'<span style="{WS};font-weight:600;font-size:24px;letter-spacing:0.1em;color:{P["mute"]}">HİCRİ {C["hicri"]}</span>' if C.get("hicri") else "")
        return (f'<div style="position:absolute;left:70px;right:70px;top:150px;display:flex;align-items:baseline;gap:22px;border-bottom:3px solid {P["rule"]};padding-bottom:18px">'
                f'<span style="{PF};font-weight:900;font-size:92px;line-height:0.9;color:{P["num"]}">{C["gunno"]}</span>'
                f'<span style="{WS};font-weight:700;font-size:40px;color:{P["month"]}">{up(C["ay"])}</span>'
                f'<span style="{PF};font-weight:900;font-size:48px;color:{P["num"]}">{C["yil"]}</span>{hic}</div>')
    return dict(band=band, date_inline=date_inline, tipo=tipo, text_block=text_block, mini=mini)

def story(C, P, X, liste_olayi=False):
    if liste_olayi:
        # "Bugün başka neler oldu?" olayları için: carousel'i olmadığından gönderi çağrısı yerine etiket ve imza
        ust = (f'<div style="flex:none;{WS};font-weight:700;font-size:30px;letter-spacing:0.22em;color:{P["month"]}">BUGÜN BAŞKA NELER OLDU?</div>')
        alt = (f'<div style="flex:none;height:84px;border-top:3px solid {P["rule"]};display:flex;align-items:center;justify-content:center;{WS}">'
               f'<span style="font-weight:600;font-size:32px;color:{P["month"]}">{e(C["hesap"])} · Takvimden bir yaprak daha.</span></div>')
    else:
        ust = ""
        alt = (f'<div style="flex:none;height:84px;border:3px solid {P["ink"]};display:flex;align-items:center;justify-content:center;{WS}">'
               f'<span style="font-weight:600;font-size:32px;color:{P["ink"]}">Hikâyenin tamamı gönderide</span></div>')
    body = (X["band"](340, 185, 268, 44) +
            f'<div style="position:absolute;left:70px;right:70px;top:390px;bottom:{1920 - SAFE_BOT}px;display:flex;flex-direction:column;gap:30px">'
            + X["date_inline"](260, 84, 104) + X["tipo"](200) + ust + X["text_block"](C["hook"], C["short"], 64, 34) + alt + '</div>')
    return page(1080, 1920, P["paper"], body)

def cover(C, P, X, n):
    body = (X["band"](170, 30, 84, 40) +
            f'<div style="position:absolute;left:70px;right:70px;top:215px;bottom:70px;display:flex;flex-direction:column;gap:26px">'
            + X["date_inline"](230, 76, 96) + X["tipo"](180) + X["text_block"](C["hook"], C["short"], 58, 32, 14) + '</div>'
            f'<div style="position:absolute;right:70px;bottom:24px;{WS};font-size:24px;color:{P["mute"]}">1 / {n}</div>')
    return page(1080, 1350, P["paper"], body)

def content(C, P, X, i, n, kicker, baslik, metin):
    body = (X["band"](110, 35) + X["mini"]() +
            f'<div style="position:absolute;left:70px;right:70px;top:330px;bottom:110px;display:flex;flex-direction:column;justify-content:center;gap:34px">'
            f'<div style="{WS};font-weight:700;font-size:28px;letter-spacing:0.28em;color:{P["month"]}">{e(up(kicker))}</div>'
            f'<h2 style="margin:0;{PF};font-weight:800;font-size:76px;line-height:1.08;color:{P["ink"]}">{e(baslik)}</h2>'
            f'<div style="width:120px;height:6px;background:{P["rule"]}"></div>'
            f'<p style="margin:0;{WS};font-size:42px;line-height:1.5;color:{P["ink"]}">{e(metin)}</p></div>'
            f'<div style="position:absolute;right:70px;bottom:26px;{WS};font-size:24px;color:{P["mute"]}">{i} / {n}</div>')
    return page(1080, 1350, P["paper"], body)

def rows_html(C, P, ysize=72, tsize=34, pad=30):
    return "".join(
        f'<div style="display:flex;gap:36px;padding:{pad}px 0;border-top:2px solid {P["hair"]}">'
        f'<div style="min-width:180px"><div style="{PF};font-weight:900;font-size:{ysize}px;line-height:1;color:{P["month"]}">{y}</div>'
        + (f'<div style="{WS};font-size:24px;color:{P["mute"]};margin-top:6px">Hicri {h}</div>' if h else '') +
        f'</div><div style="{WS};font-size:{tsize}px;line-height:1.42;color:{P["ink"]}">{e(tx)}</div></div>' for y, h, tx, *_ in C["liste"])

def liste(C, P, X, i, n):
    body = (X["band"](110, 35) + X["mini"]() +
            f'<h2 style="position:absolute;left:70px;right:70px;top:330px;margin:0;{PF};font-weight:800;font-size:72px;line-height:1.06;color:{P["ink"]}">Bugün başka neler oldu?</h2>'
            f'<div style="position:absolute;left:70px;right:70px;top:470px">{rows_html(C, P)}</div>'
            f'<div style="position:absolute;right:70px;bottom:26px;{WS};font-size:24px;color:{P["mute"]}">{i} / {n}</div>')
    return page(1080, 1350, P["paper"], body)

def slogan(C, P, X, i, n):
    body = (X["band"](200, 38) +
            f'<div style="position:absolute;left:70px;right:70px;top:330px;text-align:center">'
            f'<div style="{WS};font-weight:700;font-size:96px;line-height:1.1;letter-spacing:0.18em;color:{P["ink"]}">TARİHTE<br>BUGÜN</div>'
            f'<div style="width:300px;height:6px;background:{P["rule"]};margin:50px auto"></div>'
            f'<div style="{PF};font-weight:800;font-size:54px;line-height:1.3;color:{P["ink"]}">{e(C["slogan1"])}<br>{e(C["slogan2"])}</div>'
            f'<div style="{WS};font-weight:600;font-size:40px;color:{P["month"]};margin-top:50px">{e(C["hesap"])}</div></div>'
            f'<p style="position:absolute;left:90px;right:90px;bottom:60px;margin:0;{WS};font-size:22px;line-height:1.5;color:{P["mute"]};text-align:center">{e(C["kaynaklar"])}</p>'
            f'<div style="position:absolute;right:70px;bottom:20px;{WS};font-size:24px;color:{P["mute"]}">{i} / {n}</div>')
    return page(1080, 1350, P["paper"], body)

def story_liste(C):
    P = THEMES["normal"]; X = parts(C, P)
    body = (X["band"](340, 185, 268, 44) +
            f'<div style="position:absolute;left:70px;right:70px;top:400px;bottom:{1920 - SAFE_BOT}px;display:flex;flex-direction:column;gap:34px">'
            f'<div style="display:flex;align-items:baseline;gap:26px;border-bottom:4px solid {P["rule"]};padding-bottom:22px">'
            f'<span style="{PF};font-weight:900;font-size:150px;line-height:0.85;color:{P["num"]}">{C["gunno"]}</span>'
            f'<span style="{WS};font-weight:700;font-size:64px;color:{P["month"]}">{up(C["ay"])}</span></div>'
            f'<h1 style="margin:0;{PF};font-weight:800;font-size:76px;line-height:1.08;color:{P["ink"]}">Bugün başka neler oldu?</h1>'
            f'<div>{rows_html(C, P, 76, 38, 34)}</div>'
            f'<div style="flex:1"></div>'
            f'<div style="{WS};font-weight:600;font-size:34px;color:{P["month"]};text-align:center">@trht.bgn · Takvimden bir yaprak daha.</div></div>')
    return page(1080, 1920, P["paper"], body)

