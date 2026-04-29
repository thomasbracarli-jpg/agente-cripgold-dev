import requests
import datetime
import os
import time
# ============================================================
#   AGENTE CRIPGOLD V3.2 — Búsquedas ampliadas:
#   plata x2, diamantes x2, esmeraldas con minas,
#   LatAm extendido, bancos centrales por país
#   + Reporte HTML diario (Dashboard Premium)
# ============================================================

TOKEN         = os.environ.get("TELEGRAM_TOKEN", "8678579635:AAFbm5FMzbuDKYCnL_ttmoI0Zq5_ytRrYYM")
DESTINATARIOS = os.environ.get("TELEGRAM_CHATS", "8526092375,5503549435,6915327599").split(",")
NEWS_KEY      = os.environ.get("NEWS_API_KEY", "600c50b8de384fa88ba678ab4724d738")

# ============================================================
#   UTILIDADES
# ============================================================
def enviar_telegram(texto):
    for chat_id in DESTINATARIOS:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': texto,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        try:
            requests.post(url, data=payload, timeout=10)
        except Exception as e:
            print(f"[ERROR Telegram] chat {chat_id}: {e}")


def enviar_documento_telegram(ruta_archivo, caption=""):
    filename = os.path.basename(ruta_archivo)
    for chat_id in DESTINATARIOS:
        url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
        try:
            with open(ruta_archivo, 'rb') as f:
                files = {'document': (filename, f, 'text/html')}
                data = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                res = requests.post(url, files=files, data=data, timeout=30)
                if res.status_code == 200:
                    print(f"[REPORTE] Documento enviado a {chat_id} ✓")
                else:
                    print(f"[REPORTE] Error enviando a {chat_id}: {res.text[:120]}")
        except Exception as e:
            print(f"[REPORTE] Error enviando a {chat_id}: {e}")


def gestionar_folio(tipo):
    archivo = os.path.join(os.path.dirname(__file__), f"contador_{tipo}.txt")
    try:
        with open(archivo, "r") as f:
            actual = int(f.read().strip())
    except:
        actual = 0
    nuevo = actual + 1
    try:
        with open(archivo, "w") as f:
            f.write(str(nuevo))
    except:
        pass
    return nuevo

def gestionar_historial(titulo):
    archivo = os.path.join(os.path.dirname(__file__), "historial_noticias.txt")
    try:
        with open(archivo, "r") as f:
            historial = f.read().splitlines()
    except:
        historial = []
    clave = titulo[:60].strip()
    if clave in historial:
        return True
    historial.append(clave)
    try:
        with open(archivo, "w") as f:
            f.write("\n".join(historial[-300:]))
    except:
        pass
    return False

# ============================================================
#   TAREA 1 — PRECIOS DE COMPRA CRIPGOLD
# ============================================================
def obtener_precio_oro_cop():
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/json'
    }
    oro_usd    = None
    prev_close = None

    try:
        res = requests.get("https://data-asg.goldprice.org/dbXRates/USD", headers=headers, timeout=12)
        if res.status_code == 200:
            p = res.json()['items'][0]['xauPrice']
            if p and float(p) > 100:
                oro_usd = float(p)
                print(f"[PRECIOS] goldprice.org: ${oro_usd}")
    except Exception as e:
        print(f"[PRECIOS] goldprice.org falló: {e}")

    for ticker in (["XAUUSD=X", "GC=F"] if not oro_usd else ["GC=F", "XAUUSD=X"]):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                meta = res.json()['chart']['result'][0]['meta']
                p    = meta.get('regularMarketPrice')
                pc   = meta.get('previousClose') or meta.get('chartPreviousClose')
                if p and float(p) > 100:
                    if not oro_usd:
                        oro_usd = float(p)
                        print(f"[PRECIOS] Yahoo ({ticker}): ${oro_usd}")
                    if pc and not prev_close:
                        prev_close = float(pc)
                        print(f"[PRECIOS] Cierre anterior ({ticker}): ${prev_close}")
                    if oro_usd and prev_close:
                        break
        except:
            continue

    usd_cop = None
    try:
        res = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/COP=X?interval=1d&range=5d", headers=headers, timeout=12)
        if res.status_code == 200:
            usd_cop = float(res.json()['chart']['result'][0]['meta']['regularMarketPrice'])
    except:
        pass

    if oro_usd and usd_cop:
        gramo_cop = (oro_usd / 31.1034768) * usd_cop
        cambio_pct = None
        if prev_close and prev_close > 0:
            gramo_ayer = (prev_close / 31.1034768) * usd_cop
            cambio_pct = ((gramo_cop - gramo_ayer) / gramo_ayer) * 100
        return oro_usd, usd_cop, gramo_cop, cambio_pct
    return None, None, None, None

def construir_mensaje_precios(base_gramo, porcentaje, folio, fecha):
    base = base_gramo * porcentaje
    etiqueta = f"{int(porcentaje * 100)}%"
    def f(v):  return f"{int(v):,.0f}".replace(",", ".")
    def fr(v): return f"{int(round(v / 1000) * 1000):,.0f}".replace(",", ".")
    return (
        f"💰 <b>PRECIOS DE COMPRA CRIPGOLD</b> 💰\n"
        f"📅 <i>{fecha}    #{folio} — Base {etiqueta}</i>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n\n"
        f"<b>ORO</b>  <i>(precios exactos)</i>\n"
        f"BASE {f(base)}\n\n"
        f"18K ITALY    — {f(base * 0.74)}\n"
        f"17K NACIONAL — {f(base * 0.71)}\n"
        f"16K          — {f(base * 0.69)}\n"
        f"15K          — {f(base * 0.62)}\n"
        f"14K          — {f(base * 0.575)}\n"
        f"10K          — {f(base * 0.40)}\n\n"
        f"<b>ORO</b>  <i>(precios redondeados)</i>\n"
        f"BASE {fr(base)}\n\n"
        f"18K ITALY    — {fr(base * 0.74)}\n"
        f"17K NACIONAL — {fr(base * 0.71)}\n"
        f"16K          — {fr(base * 0.69)}\n"
        f"15K          — {fr(base * 0.62)}\n"
        f"14K          — {fr(base * 0.575)}\n"
        f"10K          — {fr(base * 0.40)}\n"
        f"➖➖➖➖➖➖➖➖➖➖"
    )

def tarea_precios(fecha):
    print("[PRECIOS] Iniciando...")
    oro_usd, usd_cop, gramo_cop, cambio_pct = obtener_precio_oro_cop()
    if not gramo_cop:
        enviar_telegram("⚠️ AGENTE CRIPGOLD — ERROR EN PRECIOS\nVerifica manualmente en finance.yahoo.com")
        return None, None, None, None
    folio = gestionar_folio("precios")

    if cambio_pct is not None:
        signo  = "+" if cambio_pct >= 0 else ""
        flecha = "📈" if cambio_pct >= 0 else "📉"
        cambio_txt = f"{flecha} <b>{signo}{cambio_pct:.2f}%</b> vs ayer"
    else:
        cambio_txt = ""

    def fmt_cop(v):
        return f"{int(round(v)):,}".replace(",", ".")

    mercado_msg = (
        f"📊 <b>Mercado hoy:</b>\n"
        f"🥇 Oro: <b>${oro_usd:,.2f} USD/oz</b>\n"
        f"💵 TRM: <b>${usd_cop:,.2f} COP/USD</b>\n"
        f"⚡ Gramo 24K: <b>${fmt_cop(gramo_cop)} COP</b>"
    )
    if cambio_txt:
        mercado_msg += f"\n{cambio_txt}"

    enviar_telegram(mercado_msg)
    enviar_telegram(construir_mensaje_precios(gramo_cop, 0.83, folio, fecha))
    enviar_telegram(construir_mensaje_precios(gramo_cop, 0.84, folio, fecha))

    if cambio_pct is not None:
        print(f"[PRECIOS] OK — gramo 24K: ${fmt_cop(gramo_cop)} COP | cambio: {cambio_pct:.2f}%")
    else:
        print(f"[PRECIOS] OK — gramo 24K: ${fmt_cop(gramo_cop)} COP")

    return oro_usd, usd_cop, gramo_cop, cambio_pct

# ============================================================
#   TAREA 1B — DASHBOARD HTML DE PRECIOS (interno CripGold)
# ============================================================

def generar_dashboard_precios_html(oro_usd, usd_cop, gramo_cop, cambio_pct, fecha):
    import tempfile

    def f(v):   return f"{int(v):,.0f}".replace(",", ".")
    def fr(v):  return f"{int(round(v / 1000) * 1000):,.0f}".replace(",", ".")
    def fk(v):  return f"{int(round(v)):,}".replace(",", ".")

    base83 = gramo_cop * 0.83
    base84 = gramo_cop * 0.84

    if cambio_pct is not None:
        signo     = "+" if cambio_pct >= 0 else ""
        color_var = "#00FF88" if cambio_pct >= 0 else "#FF1E4A"
        flecha    = "▲" if cambio_pct >= 0 else "▼"
        cambio_str = f"{flecha} {signo}{cambio_pct:.2f}%"
    else:
        color_var  = "#FFD700"
        cambio_str = "—"

    now_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

    QUILATES = [
        ('18K ITALY',    0.740, 'Estándar internacional'),
        ('17K NACIONAL', 0.710, 'El más cotizado'),
        ('16K',          0.690, ''),
        ('15K',          0.620, ''),
        ('14K',          0.575, ''),
        ('10K',          0.400, 'Joyería moderna'),
    ]

    def tabla_html(base, pct_label):
        filas = ""
        for nombre, pct, nota in QUILATES:
            val_ex  = f(base * pct)
            val_rd  = fr(base * pct)
            nota_td = f'<span class="nota">{nota}</span>' if nota else ''
            filas += (
                f'<tr>'
                f'<td class="quilate">{nombre}{nota_td}</td>'
                f'<td class="precio exacto">{val_ex}</td>'
                f'<td class="precio redondeado">{val_rd}</td>'
                f'</tr>'
            )
        return (
            f'<div class="table-wrap">'
            f'<div class="table-header">'
            f'  <span class="tbl-label">BASE {pct_label}</span>'
            f'  <span class="tbl-base">{f(base)}</span>'
            f'  <span class="tbl-base-rd">· {fr(base)} redondeado</span>'
            f'</div>'
            f'<table>'
            f'<thead><tr>'
            f'<th>QUILATE</th><th>EXACTO</th><th>REDONDEADO</th>'
            f'</tr></thead>'
            f'<tbody>{filas}</tbody>'
            f'</table>'
            f'</div>'
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>CripGold · Precios {fecha}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --gold:#FFD700;--gold-dk:#B8860B;--gold-dim:#6a5400;
  --bg:#0C0C0C;--bg2:#121212;--bg3:#181818;
  --text:#E8E8E0;--dim:#777;
  --border:rgba(255,215,0,.13);--border2:rgba(255,215,0,.22);
}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}}
.hdr{{background:linear-gradient(135deg,#090909 0%,#160f00 50%,#090909 100%);border-bottom:1px solid var(--border);padding:32px 32px 20px;text-align:center;position:relative;overflow:hidden}}
.hdr::before{{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 70% 90% at 50% -10%,rgba(255,215,0,.07) 0%,transparent 70%);pointer-events:none}}
.logo{{font-family:'Playfair Display',serif;font-size:42px;font-weight:900;letter-spacing:8px;background:linear-gradient(135deg,#FFD700,#FFFDE0,#B8860B);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1}}
.logo-sub{{font-size:11px;letter-spacing:5px;color:var(--gold-dim);margin-top:4px;text-transform:uppercase}}
.hdr-date{{margin-top:12px;font-size:12px;color:var(--dim);letter-spacing:2px}}
.hdr-date b{{color:var(--gold)}}
.ticker{{display:flex;justify-content:center;align-items:stretch;flex-wrap:wrap;background:rgba(255,215,0,.04);border:1px solid var(--border);border-radius:14px;margin:20px auto 0;max-width:860px;overflow:hidden}}
.tk-item{{padding:16px 14px;text-align:center;flex:1;min-width:120px}}
.tk-sep{{width:1px;background:var(--border);align-self:stretch;flex-shrink:0}}
.tk-lbl{{font-size:9px;letter-spacing:2px;color:var(--gold-dim);text-transform:uppercase;margin-bottom:5px}}
.tk-val{{font-size:17px;font-weight:700;color:var(--gold);line-height:1}}
.tk-unit{{font-size:10px;color:var(--dim);margin-top:3px}}
.tk-cambio{{font-size:15px;font-weight:700;color:{color_var};line-height:1}}
.main{{max-width:900px;margin:0 auto;padding:32px 20px 60px}}
.table-wrap{{background:var(--bg3);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:28px}}
.table-header{{display:flex;align-items:baseline;gap:12px;padding:16px 22px;background:rgba(255,215,0,.04);border-bottom:1px solid var(--border)}}
.tbl-label{{font-size:10px;letter-spacing:4px;color:var(--gold-dk);text-transform:uppercase;font-weight:600}}
.tbl-base{{font-family:'Playfair Display',serif;font-size:26px;font-weight:700;color:var(--gold);margin-left:8px}}
.tbl-base-rd{{font-size:12px;color:var(--dim);letter-spacing:1px}}
table{{width:100%;border-collapse:collapse}}
thead tr{{background:rgba(255,215,0,.05)}}
th{{padding:11px 22px;text-align:left;font-size:9px;letter-spacing:3px;color:var(--gold-dim);text-transform:uppercase;font-weight:500;border-bottom:1px solid var(--border)}}
th:not(:first-child){{text-align:right}}
td{{padding:13px 22px;border-bottom:1px solid rgba(255,215,0,.05)}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:rgba(255,215,0,.04)}}
.quilate{{font-size:14px;font-weight:500;color:var(--text);display:flex;flex-direction:column;gap:2px}}
.nota{{font-size:10px;color:var(--dim);letter-spacing:1px;font-weight:400}}
.precio{{text-align:right;font-size:15px;font-weight:600;font-family:'Playfair Display',serif}}
.exacto{{color:var(--gold)}}
.redondeado{{color:rgba(255,215,0,0.55)}}
.ftr{{text-align:center;padding:24px;border-top:1px solid var(--border);color:var(--dim);font-size:11px;letter-spacing:1px;margin-top:8px}}
.ftr b{{color:var(--gold-dk)}}
body::after{{content:'';position:fixed;inset:0;pointer-events:none;z-index:999;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.025) 2px,rgba(0,0,0,.025) 4px)}}
@media(max-width:600px){{.ticker{{flex-direction:column}}.tk-sep{{width:100%;height:1px}}.tbl-base{{font-size:20px}}}}
</style>
</head>
<body>
<div class="hdr">
  <div class="logo">CRIPGOLD</div>
  <div class="logo-sub">Dashboard de Precios &nbsp;·&nbsp; Uso Interno</div>
  <div class="hdr-date">📅 <b>{fecha}</b> &nbsp;·&nbsp; {now_str}</div>
  <div class="ticker">
    <div class="tk-item"><div class="tk-lbl">🥇 Oro Spot</div><div class="tk-val">${oro_usd:,.2f}</div><div class="tk-unit">USD/oz</div></div>
    <div class="tk-sep"></div>
    <div class="tk-item"><div class="tk-lbl">💱 TRM</div><div class="tk-val">${usd_cop:,.2f}</div><div class="tk-unit">COP/USD</div></div>
    <div class="tk-sep"></div>
    <div class="tk-item"><div class="tk-lbl">⚡ Gramo 24K</div><div class="tk-val">{fk(gramo_cop)}</div><div class="tk-unit">COP</div></div>
    <div class="tk-sep"></div>
    <div class="tk-item"><div class="tk-lbl">📊 Variación</div><div class="tk-cambio">{cambio_str}</div><div class="tk-unit">vs ayer</div></div>
  </div>
</div>
<div class="main">
  {tabla_html(base83, '83%')}
  {tabla_html(base84, '84%')}
</div>
<div class="ftr">
  Generado por <b>Agente CripGold V3.2</b> &nbsp;·&nbsp; {now_str}<br>
  Documento interno &nbsp;·&nbsp; No compartir públicamente
</div>
</body>
</html>"""

    nombre = f"precios_cripgold_{datetime.datetime.now().strftime('%Y%m%d')}.html"
    ruta   = os.path.join(tempfile.gettempdir(), nombre)
    with open(ruta, 'w', encoding='utf-8') as fh:
        fh.write(html)

    print(f"[DASHBOARD] HTML generado: {ruta} ({os.path.getsize(ruta):,} bytes)")

    caption = (
        f"💰 <b>Dashboard de Precios CripGold</b> · {fecha}\n"
        f"🥇 Oro: ${oro_usd:,.2f} USD/oz\n"
        f"⚡ Gramo 24K: {fk(gramo_cop)} COP\n"
        f"📊 Variación: <b>{cambio_str}</b> vs ayer"
    )
    enviar_documento_telegram(ruta, caption)
    print("[DASHBOARD] Enviado a todos los destinatarios.")
    return ruta


# ============================================================
#   TAREA 2 — NOTICIAS V3.2
# ============================================================

def normalizar_titulo(titulo):
    import re
    STOPWORDS = {
        'el','la','los','las','un','una','de','del','en','y','a','que','con',
        'por','para','se','su','sus','al','es','son','ha','han','le','lo',
        'todo','toda','este','esta','como','pero','mas','muy','ya','si','no',
        'o','e','ni','sobre','entre','tras','ante','bajo','desde','hasta',
        'hacia','sin','pro','vs'
    }
    t = titulo.lower()
    t = re.sub(r'\d{1,2} de \w+ de \d{4}', '', t)
    t = re.sub(r'(lunes|martes|miercoles|jueves|viernes|sabado|domingo)', '', t)
    t = re.sub(r'\d+', '', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    palabras = [p for p in t.split() if p not in STOPWORDS and len(p) > 3]
    return ' '.join(palabras[:6])

DOMINIOS_BLOQUEADOS_FUENTE = [
    "vietnam.vn","vietstock.vn","vnexpress","thanhnien",
    "tuoitre","baodautu","cafef.vn","tinnhanhchungkhoan",
]

BASURA = [
    "precio del oro en sjc","anillos de oro de 9999","precio del oro en vietnam",
    "vnd por onza","sjc, precio del oro","tael de oro",
    "free fire","freefire","códigos de hoy","recompensas gratis",
    "league of legends","clash of clans","fortnite","valorant","pubg",
    "mobile legends","rango de oro","rango de plata","rango de diamante",
    "temporada de juego","pase de batalla","loot box",
    "medalla de oro","medalla de plata","medalla de bronce",
    "medallas de oro","medallas de plata","medallas de bronce",
    "copa oro","copa de oro","copa america","copa del mundo","copa mundo",
    "liga de naciones","liga de futbol","liga de fútbol",
    "juegos olímpicos","juegos olimpicos","juegos panamericanos",
    "juegos suramericanos","suramericanos de la juventud",
    "juegos bolivarianos","juegos centroamericanos","juegos deportivos",
    "balón de oro","bota de oro","guante de oro","gol de oro",
    "podio","podio de oro","campeón de oro","campeonato",
    "torneo de futbol","torneo de fútbol","mundial de futbol",
    "nba","nfl","champions","premier league","laliga","serie a",
    "atletismo","ciclismo","tenis","boxeo","natación","rugby",
    "transmitirá netflix","transmitira netflix","liga de naciones en méxico",
    "premio platino","premios platino","golden globe","bafta","emmy",
    "grammy","bts","kpop","concierto","gira musical",
    "actor","actriz","estreno de","película","serie de televisión",
    "lució","llevó puesto","vistió con","reina camilla","kate middleton",
    "meghan markle","alfombra roja","look de","outfit","tendencia de moda",
    "colección de joyas","joya real","novia real","boda real",
    "corazón de oro","edad de oro","regla de oro","color dorado",
    "boda de plata","disco de oro","voz de oro","manos de oro",
    "toque de oro","momento de oro","oportunidad de oro",
    "generación de oro","generacion de oro","era dorada","época dorada",
    "época de oro","sello de oro","récord de oro",
    "mar del plata","río de la plata","sierra de oro",
    "ganar el oro","ganó el oro","se llevó el oro","conquistó el oro",
    "el oro del mundial","el oro en el mundial","medalla dorada",
    "mundial júnior","mundial junior","mundial de taekwondo","mundial de natación",
    "mundial de atletismo","mundial de ciclismo","mundial de boxeo","mundial de judo",
    "mundial de halterofilia","mundial de gimnasia","mundial de lucha","mundial de esgrima",
    "tricampeón","bicampeón","pentacampeón","campeón del mundo de","subcampeón del mundo",
    "se colgó la medalla","se colgó el oro","colgó medalla","ganó medalla",
    "clasificó para","avanzó a semifinal","avanzó a la final","pasó a la final",
    "juegos mundiales","juegos universitarios","juegos escolares",
    "record mundial de","récord mundial de","nuevo récord en los",
    "federación de","selección de","equipo nacional de","representó a",
    "podio en","subió al podio","en el podio",
    "taekwondo","judo","halterofilia","esgrima","tiro con arco","pentatlon",
    "decatlon","heptatlón","maratón","triatlón","remo","canoa","vela","polo",
    "hockey","voleibol","baloncesto","balonmano","waterpolo","handball",
    "estafa","robo de","hurto de","arrestaron","capturaron","secuestro","homicidio",
    "plazo fijo","cepo al dólar","dólar blue",
    "granos","soja","trigo","maíz","cosecha","ganadería",
    "tarjeta de crédito","billete","papel moneda",
    "samsung","xiaomi","iphone","receta","cocina","celular","smartphone","biblioteca",
    "inundacion","inundaciones","escuela","colegio","carretera","vía terciaria",
    "acueducto","alcantarillado","alcalde","gobernación pide","comunidad pide",
    "pide a muzo","pide a chivor","vías de acceso",
]

CONTEXTO_ORO = [
    "precio del oro","cotización del oro","onza de oro","onza troy",
    "mercado del oro","reservas de oro","lingote de oro","lingotes de oro",
    "minería de oro","minería aurífera","oro físico","producción de oro",
    "inversión en oro","demanda de oro","activo de oro","fondo de oro",
    "etf de oro","futuros del oro","precio spot del oro","récord del oro",
    "máximo histórico del oro","repatriación de oro","minería ilegal de oro",
    "brics","bancos centrales","reserva en oro","banco central",
    "xau","gold price","gold market",
]

CONTEXTO_ESMERALDA = [
    "esmeralda","esmeraldas","piedra preciosa","piedras preciosas",
    "gema","gemas","joya","joyas","quilate","exportación de esmeraldas",
    "mercado de esmeraldas","precio de esmeraldas","sector esmeraldero",
    "fedesmeraldas","minería de esmeraldas","mina de esmeraldas",
    "esmeralda colombiana","esmeraldas colombianas",
]

PALABRAS_PRECIO_ORO = [
    "precio del oro","cotización del oro","xau/usd","precio spot",
    "precio de la onza","sube el oro","baja el oro","cae el oro",
    "onza de oro","precio hoy","cotización hoy",
]

CATEGORIAS = {
    'oro': {
        'target': 7,
        'emoji': '🥇',
        'label': 'ORO',
        'tema': 3,
        'queries': [
            '(Colombia OR Medellín OR Bogotá OR Boyacá OR Antioquia OR Venezuela OR Perú OR México OR Argentina OR Ecuador OR Chile OR Bolivia OR Uruguay OR Brasil) AND ("oro" OR "minería aurífera" OR "producción de oro" OR "reservas de oro")',
            '("oro" OR "minería de oro") AND (Colombia OR "BanRep" OR "Banco de la República" OR "Minhacienda" OR "ANM")',
            '("banco central" OR "reservas internacionales") AND "oro" AND (Colombia OR Venezuela OR Perú OR México OR Argentina OR Ecuador OR Chile OR Bolivia)',
            '"oro" AND ("guerra" OR "aranceles" OR "Trump" OR "Irán" OR "tensión" OR "repatriación" OR "sanciones" OR "Oriente Medio" OR "OPEP" OR "estrecho de Ormuz")',
            '"reservas de oro" OR "repatriación de oro" OR ("banco central" AND "oro") OR ("brics" AND "oro") OR "lingote de oro" OR ("Turquía" AND "oro") OR ("China" AND "reservas de oro")',
            '"precio del oro" AND ("análisis" OR "pronóstico" OR "previsión" OR "resistencia" OR "soporte" OR "alcista" OR "bajista" OR "objetivo" OR "meta")',
            '"producción de oro" OR "minería aurífera" OR ("inversión" AND "oro") OR "ETF de oro" OR "récord del oro" OR "fondo de oro" OR "demanda de oro"',
            '"precio del oro hoy" OR "cotización del oro" OR "XAU/USD" OR "onza de oro" OR "precio spot del oro"',
        ],
    },
    'plata': {
        'target': 2,
        'emoji': '🥈',
        'label': 'PLATA',
        'tema': 5,
        'queries': [
            '"precio de la plata" OR "cotización de la plata" OR "XAG/USD" OR "mercado de la plata" OR "onza de plata"',
            '"plata" AND ("análisis" OR "rally" OR "caída" OR "máximo" OR "mínimo" OR "tendencia" OR "inversión" OR "resistencia" OR "soporte")',
            '"déficit de plata" OR "demanda de plata" OR "ETF de plata" OR "ratio oro plata" OR "Silver Institute" OR "Instituto de la Plata" OR "superávit de plata"',
            '"plata industrial" OR "demanda industrial de plata" OR "plata solar" OR "plata electrónica" OR ("plata" AND "energía renovable")',
        ],
    },
    'diamante': {
        'target': 2,
        'emoji': '💎',
        'label': 'DIAMANTES',
        'tema': 4,
        'queries': [
            '"mercado de diamantes" OR "industria del diamante" OR "diamantes de laboratorio" OR "De Beers" OR "crisis del diamante" OR "mina de diamantes" OR "diamante sintético"',
            '"diamante" AND ("precio" OR "inversión" OR "sintético" OR "cierre" OR "récord" OR "tendencia" OR "mercado" OR "demanda" OR "cotización")',
            '("Sotheby\'s" OR "Christie\'s" OR "Bonhams") AND ("diamante" OR "gema" OR "joya" OR "piedra preciosa")',
            '"subasta de diamante" OR "diamante subasta" OR "récord de subasta" OR "diamante récord" OR "diamante más caro"',
        ],
    },
    'esmeralda': {
        'target': 1,
        'emoji': '💚',
        'label': 'ESMERALDAS',
        'tema': 2,
        'queries': [
            '"esmeraldas colombianas" OR "sector esmeraldero" OR "Fedesmeraldas" OR "exportación de esmeraldas" OR "mercado de esmeraldas"',
            '"esmeralda" AND ("precio" OR "mercado" OR "exportación" OR "inversión" OR "quilate" OR "joya" OR "piedra preciosa" OR "gema")',
            'Colombia AND ("esmeralda" OR "esmeraldas") AND ("precio" OR "mercado" OR "exportación" OR "quilate" OR "mina")',
            '("Muzo" OR "Chivor" OR "Coscuez") AND ("esmeralda" OR "gema" OR "piedra preciosa" OR "mina" OR "exportación")',
            '"gemas colombianas" OR "piedras preciosas colombianas" OR "esmeralda colombiana" OR (Colombia AND "gemas" AND "exportación")',
        ],
    },
}

def obtener_noticias():
    import xml.etree.ElementTree as ET
    import urllib.parse
    import re as _re
    from email.utils import parsedate_to_datetime

    ahora    = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    hace_72h = ahora - datetime.timedelta(hours=72)

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    }

    resultados     = {cat: [] for cat in CATEGORIAS}
    titulos_vistos = set()
    precio_oro_count = [0]

    def fetch_items(query):
        q_enc = urllib.parse.quote(query)
        url   = (f"https://news.google.com/rss/search"
                 f"?q={q_enc}&hl=es-419&gl=CO&ceid=CO:es")
        res   = requests.get(url, headers=headers, timeout=15)
        root  = ET.fromstring(res.content)
        return root.findall('.//item')

    def validar(item, categoria):
        titulo   = (item.findtext('title')       or '').strip()
        link     = (item.findtext('link')        or '').strip()
        pub_date = (item.findtext('pubDate')     or '').strip()
        desc_raw = (item.findtext('description') or '').strip()

        if not titulo or not link:
            return None

        src_elem = item.find('source')
        src_name = ''
        if src_elem is not None:
            src_name = (src_elem.text or '').strip()
            fuente = (src_name + ' ' + (src_elem.get('url') or '')).lower()
            if any(d in fuente for d in DOMINIOS_BLOQUEADOS_FUENTE):
                return None

        try:
            if parsedate_to_datetime(pub_date) < hace_72h:
                return None
        except Exception:
            pass

        texto       = (titulo + ' ' + desc_raw).lower()
        titulo_solo = titulo.lower()

        if any(b in texto for b in BASURA):
            return None
        if any(b in titulo_solo for b in BASURA):
            return None

        if categoria == 'oro' and not any(c in titulo_solo for c in CONTEXTO_ORO):
            return None
        if categoria == 'esmeralda' and not any(c in texto for c in CONTEXTO_ESMERALDA):
            return None

        if categoria == 'oro':
            es_precio = any(kw in texto for kw in PALABRAS_PRECIO_ORO)
            if es_precio:
                if precio_oro_count[0] >= 1:
                    return None
                precio_oro_count[0] += 1

        if gestionar_historial(titulo):
            return None

        clave = normalizar_titulo(titulo)
        if clave in titulos_vistos:
            return None

        desc_clean = _re.sub(r'<[^>]+>', ' ', desc_raw)
        for _e, _r in [('&nbsp;',' '),('&amp;','&'),('&lt;','<'),('&gt;','>'),('&quot;','"'),('&#39;',"'")]:
            desc_clean = desc_clean.replace(_e, _r)
        desc_clean = ' '.join(desc_clean.split())
        if len(desc_clean) > 200:
            desc_clean = desc_clean[:200].rsplit(' ', 1)[0] + '…'

        return titulo, link, desc_clean, src_name

    for cat_name, cat in CATEGORIAS.items():
        target = cat['target']
        print(f"\n[NOTICIAS] ── {cat['emoji']} {cat['label']} (objetivo: {target}) ──")

        for query in cat['queries']:
            if len(resultados[cat_name]) >= target:
                break
            try:
                items = fetch_items(query)
                for item in items:
                    if len(resultados[cat_name]) >= target:
                        break
                    resultado = validar(item, cat_name)
                    if resultado:
                        titulo, link, desc, source = resultado
                        titulos_vistos.add(normalizar_titulo(titulo))
                        resultados[cat_name].append({
                            'title':  titulo,
                            'url':    link,
                            'desc':   desc,
                            'source': source,
                            'tema':   cat['tema'],
                        })
                        print(f"  ✓ {titulo[:70]}")
                time.sleep(0.8)
            except Exception as e:
                print(f"  [ERROR] {cat_name}: {e}")

        encontradas = len(resultados[cat_name])
        estado      = "✅" if encontradas >= target else f"⚠️  solo {encontradas}/{target}"
        print(f"  → {cat['label']}: {encontradas}/{target} {estado}")

    total = sum(len(v) for v in resultados.values())
    print(f"\n[NOTICIAS] Total: {total} noticias")
    return resultados

def tarea_noticias(fecha):
    print("[NOTICIAS] Iniciando...")
    resultados = obtener_noticias()
    total = sum(len(v) for v in resultados.values())

    if total == 0:
        enviar_telegram(
            "⚠️ <b>AGENTE CRIPGOLD — SIN NOTICIAS</b>\n"
            "No se encontraron noticias nuevas en las últimas 72h."
        )
        return []

    folio = gestionar_folio("noticias")
    msg   = (
        f"💎 <b>NOTICIAS — METALES Y GEMAS</b> 🏆\n"
        f"📅 <i>{fecha}    #{folio}</i>\n\n"
    )

    contador = 1
    for cat_name, cat in CATEGORIAS.items():
        arts = resultados[cat_name]
        msg += f"{cat['emoji']} <b>{cat['label']}</b>\n"
        if not arts:
            if cat_name == 'esmeralda':
                msg += "<i>Sin noticias de mercado esta semana.</i>\n"
            else:
                msg += "<i>Sin resultados obtenidos.</i>\n"
        else:
            for art in arts:
                src_tag = f" · <i>{art['source']}</i>" if art.get('source') else ""
                msg += f"<b>{contador}.</b> <a href='{art['url']}'>{art['title']}</a>{src_tag}\n"
                contador += 1
        msg += "\n"

    msg += "🤖 <i>Agente CripGold V3.2 — Investigación finalizada.</i>"
    enviar_telegram(msg)
    print(f"[NOTICIAS] OK — {total} noticias enviadas.")

    arts_plana = []
    for cat_name in CATEGORIAS:
        arts_plana.extend(resultados[cat_name])
    return arts_plana

# ============================================================
#   TAREA 3 — REPORTE HTML DIARIO (Dashboard Premium Noticias)
# ============================================================

def generar_reporte_html(arts, fecha, oro_usd=None, usd_cop=None):
    import tempfile
    import re as _re

    def esc(t):
        return (t or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    TEMAS = [
        (2, "🇨🇴", "Colombia &amp; Esmeraldas",  "#f5c842"),
        (3, "📈",  "Cotización &amp; Precio",      "#2ecc71"),
        (4, "💎",  "Diamantes",                    "#b389e8"),
        (5, "⚪",  "Plata &amp; Platino",           "#a0aec0"),
    ]

    all_text = ' '.join((a['title']+' '+a.get('desc','')).lower() for a in arts)
    BULLISH = ['récord','record','sube','subió','máximo','demanda','rally','alza','aumenta','fuerte','histórico','supera','crece','boom','impulsa']
    BEARISH = ['cae','cayó','baja','bajó','crisis','presión','disminuye','pierde','débil','mínimo','colapso','desploma','riesgo','contracción']
    sent = 50
    for a in arts:
        t = (a['title']+' '+a.get('desc','')).lower()
        sent += sum(3 for w in BULLISH if w in t)
        sent -= sum(3 for w in BEARISH if w in t)
    sent = max(5, min(95, sent))

    if   sent >= 65: sent_label, sent_color = 'ALCISTA', '#2ecc71'
    elif sent >= 45: sent_label, sent_color = 'NEUTRAL',  '#f39c12'
    else:            sent_label, sent_color = 'BAJISTA',  '#e74c3c'

    def kw(words): return sum(1 for w in words if w in all_text)
    geo_arts = [a for a in arts if 'guerra' in (a['title']+a.get('desc','')).lower() or 'trump' in (a['title']+a.get('desc','')).lower() or 'aranceles' in (a['title']+a.get('desc','')).lower()]
    bc_arts  = [a for a in arts if 'banco central' in (a['title']+a.get('desc','')).lower() or 'brics' in (a['title']+a.get('desc','')).lower() or 'reservas' in (a['title']+a.get('desc','')).lower()]
    min_arts = [a for a in arts if 'minería' in (a['title']+a.get('desc','')).lower() or 'producción' in (a['title']+a.get('desc','')).lower()]

    ind_bc  = min(95, 40 + len(bc_arts)*12  + kw(['banco central','reservas','brics','repatriación'])*6)
    ind_min = min(95, 35 + len(min_arts)*11 + kw(['producción','minería','toneladas','extracción','récord'])*5)
    ind_inv = sent
    ind_vol = min(95, 15 + len(geo_arts)*15 + kw(['guerra','tensión','misil','aranceles','trump','conflicto'])*8)

    gramo_24k = gramo_18k = gramo_14k = 0.0
    if oro_usd and usd_cop:
        gramo_24k = (oro_usd / 31.1034768) * usd_cop
        gramo_18k = gramo_24k * 0.74
        gramo_14k = gramo_24k * 0.575

    grupos = {}
    for a in arts:
        grupos.setdefault(a.get('tema', 3), []).append(a)

    headline = arts[0] if arts else None
    now_str  = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

    CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--gold:#FFD700;--gold-dk:#B8860B;--gold-dim:#6a5400;--bg:#0C0C0C;--bg2:#121212;--bg3:#181818;--bg4:#1e1e1e;--text:#E8E8E0;--dim:#777;--border:rgba(255,215,0,.13);--border2:rgba(255,215,0,.22);}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}
.hdr{background:linear-gradient(135deg,#090909 0%,#160f00 50%,#090909 100%);border-bottom:1px solid var(--border);padding:36px 32px 24px;text-align:center;position:relative;overflow:hidden}
.hdr::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 70% 90% at 50% -10%,rgba(255,215,0,.07) 0%,transparent 70%);pointer-events:none}
.logo{font-family:'Playfair Display',serif;font-size:46px;font-weight:900;letter-spacing:8px;background:linear-gradient(135deg,#FFD700,#FFFDE0,#B8860B);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1}
.logo-sub{font-size:11px;letter-spacing:5px;color:var(--gold-dim);margin-top:5px;text-transform:uppercase}
.hdr-date{margin-top:14px;font-size:12px;color:var(--dim);letter-spacing:2px}
.hdr-date b{color:var(--gold)}
.ticker{display:flex;justify-content:center;align-items:stretch;flex-wrap:wrap;background:rgba(255,215,0,.04);border:1px solid var(--border);border-radius:14px;margin:24px auto 0;max-width:920px;overflow:hidden}
.tk-item{padding:18px 16px;text-align:center;flex:1;min-width:130px}
.tk-sep{width:1px;background:var(--border);align-self:stretch;flex-shrink:0}
.tk-lbl{font-size:9px;letter-spacing:2px;color:var(--gold-dim);text-transform:uppercase;margin-bottom:6px}
.tk-val{font-size:18px;font-weight:700;color:var(--gold);line-height:1}
.tk-unit{font-size:10px;color:var(--dim);margin-top:3px}
.main{max-width:960px;margin:0 auto;padding:36px 24px 60px}
.dash-row{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:40px}
.dash-box{background:var(--bg3);border:1px solid var(--border);border-radius:14px;padding:24px}
.dash-title{font-size:10px;letter-spacing:3px;color:var(--gold-dk);text-transform:uppercase;margin-bottom:20px}
.sent-score{text-align:center;margin-bottom:20px}
.sent-num{font-family:'Playfair Display',serif;font-size:52px;font-weight:900;line-height:1}
.sent-lbl{font-size:13px;letter-spacing:3px;margin-top:6px;font-weight:600}
.gauge-track{height:10px;border-radius:5px;background:linear-gradient(to right,#e74c3c 0%,#f39c12 50%,#2ecc71 100%);position:relative;margin:10px 0 6px}
.gauge-needle{position:absolute;top:-5px;width:3px;height:20px;background:#fff;border-radius:2px;transform:translateX(-50%);box-shadow:0 0 8px rgba(255,255,255,.6)}
.gauge-labels{display:flex;justify-content:space-between;font-size:9px;color:var(--dim);letter-spacing:1px}
.ind-row{margin-bottom:16px}
.ind-label{font-size:9px;letter-spacing:2px;color:var(--dim);text-transform:uppercase;margin-bottom:6px}
.ind-track{height:6px;background:rgba(255,255,255,.07);border-radius:3px;overflow:hidden}
.ind-fill{height:100%;border-radius:3px}
.ind-pct{font-size:11px;color:var(--text);margin-top:4px;text-align:right}
.sec-label{font-size:10px;letter-spacing:4px;color:var(--gold-dk);text-transform:uppercase;margin-bottom:6px}
.sec-title{font-family:'Playfair Display',serif;font-size:24px;font-weight:700;color:var(--text);margin-bottom:28px;padding-bottom:12px;border-bottom:1px solid var(--border)}
.grupo{margin-bottom:32px}
.grupo-hdr{display:flex;align-items:center;gap:10px;padding:10px 16px;background:var(--bg3);border:1px solid var(--border);border-radius:10px 10px 0 0;border-bottom:none}
.grupo-icon{font-size:16px}
.grupo-name{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--text);font-weight:600;flex:1}
.grupo-cnt{font-size:10px;background:rgba(255,215,0,.1);border:1px solid var(--border);border-radius:20px;padding:2px 10px;color:var(--gold-dk)}
.art-card{display:flex;background:rgba(255,215,0,.03);border:1px solid var(--border);border-top:none;transition:background .2s,border-color .2s}
.art-card:last-child{border-radius:0 0 10px 10px}
.art-card:hover{background:rgba(255,215,0,.07);border-color:var(--border2)}
.art-stripe{width:4px;flex-shrink:0}
.art-body{padding:14px 18px;flex:1}
.art-title{display:block;font-size:14px;font-weight:500;color:var(--text);text-decoration:none;line-height:1.5;margin-bottom:5px}
.art-title:hover{color:var(--gold)}
.art-src{display:inline-block;font-size:10px;color:var(--gold-dim);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}
.art-desc{font-size:12.5px;color:#999;line-height:1.65;margin-top:2px}
.ref-box{background:linear-gradient(135deg,rgba(255,215,0,.05),rgba(255,215,0,.02));border:1px solid var(--border2);border-radius:14px;padding:32px 36px;margin-top:40px;position:relative;overflow:hidden}
.ref-box::before{content:'"';position:absolute;top:-10px;left:20px;font-size:120px;color:rgba(255,215,0,.06);font-family:'Playfair Display',serif;line-height:1}
.ref-lbl{font-size:9px;letter-spacing:4px;color:var(--gold-dk);text-transform:uppercase;margin-bottom:16px}
.ref-text{font-family:'Playfair Display',serif;font-size:20px;font-style:italic;color:var(--text);line-height:1.6}
.ref-src{display:block;margin-top:14px;font-size:11px;color:var(--dim);letter-spacing:2px}
.ftr{text-align:center;padding:28px 24px;border-top:1px solid var(--border);color:var(--dim);font-size:11px;letter-spacing:1px;margin-top:20px}
.ftr b{color:var(--gold-dk)}
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:999;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.025) 2px,rgba(0,0,0,.025) 4px)}
@media(max-width:640px){.dash-row{grid-template-columns:1fr}.ticker{flex-direction:column}.tk-sep{width:100%;height:1px}}
"""

    if oro_usd and usd_cop:
        ticker_html = (
            f'<div class="tk-item"><div class="tk-lbl">🥇 ORO SPOT</div><div class="tk-val">${oro_usd:,.2f}</div><div class="tk-unit">USD/oz</div></div>'
            f'<div class="tk-sep"></div>'
            f'<div class="tk-item"><div class="tk-lbl">💱 TRM</div><div class="tk-val">${usd_cop:,.2f}</div><div class="tk-unit">COP/USD</div></div>'
            f'<div class="tk-sep"></div>'
            f'<div class="tk-item"><div class="tk-lbl">⚡ GRAMO 24K</div><div class="tk-val">${gramo_24k:,.0f}</div><div class="tk-unit">COP</div></div>'
            f'<div class="tk-sep"></div>'
            f'<div class="tk-item"><div class="tk-lbl">✨ GRAMO 18K</div><div class="tk-val">${gramo_18k:,.0f}</div><div class="tk-unit">COP</div></div>'
            f'<div class="tk-sep"></div>'
            f'<div class="tk-item"><div class="tk-lbl">🔸 GRAMO 14K</div><div class="tk-val">${gramo_14k:,.0f}</div><div class="tk-unit">COP</div></div>'
        )
    else:
        ticker_html = '<div class="tk-item" style="color:#B8860B;text-align:center;width:100%;">Precios no disponibles hoy</div>'

    def ind_bar(label, pct, color):
        return (f'<div class="ind-row"><div class="ind-label">{label}</div>'
                f'<div class="ind-track"><div class="ind-fill" style="width:{pct}%;background:{color};"></div></div>'
                f'<div class="ind-pct">{pct}%</div></div>')

    indicators_html = (
        ind_bar("DEMANDA BANCOS CENTRALES", ind_bc,  "#4a9edd") +
        ind_bar("ACTIVIDAD MINERA GLOBAL",  ind_min, "#e8965a") +
        ind_bar("SENTIMIENTO INVERSOR",     ind_inv, sent_color) +
        ind_bar("VOLATILIDAD GEOPOLÍTICA",  ind_vol, "#e05252")
    )

    grupos_html = ""
    for tema_id, icon, label, color in TEMAS:
        if tema_id not in grupos:
            continue
        cards_html = ""
        for a in grupos[tema_id]:
            src_tag  = f'<span class="art-src">{esc(a["source"])}</span>' if a.get('source') else ''
            desc_tag = f'<p class="art-desc">{esc(a["desc"])}</p>'        if a.get('desc')   else ''
            cards_html += (
                f'<div class="art-card"><div class="art-stripe" style="background:{color};"></div>'
                f'<div class="art-body"><a href="{a["url"]}" target="_blank" class="art-title">{esc(a["title"])}</a>'
                f'{src_tag}{desc_tag}</div></div>'
            )
        n = len(grupos[tema_id])
        grupos_html += (
            f'<div class="grupo"><div class="grupo-hdr">'
            f'<span class="grupo-icon">{icon}</span>'
            f'<span class="grupo-name">{label}</span>'
            f'<span class="grupo-cnt">{n} noticia{"s" if n>1 else ""}</span>'
            f'</div>{cards_html}</div>'
        )

    ref_text = esc(headline['title']) if headline else 'Sin titular destacado hoy.'
    ref_src  = esc(headline.get('source','')) if headline else ''

    html = (
        f'<!DOCTYPE html>\n<html lang="es">\n<head>\n'
        f'<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        f'<title>CripGold · Dashboard {fecha}</title>\n'
        f'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        f'<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">\n'
        f'<style>{CSS}</style>\n</head>\n<body>\n\n'
        f'<div class="hdr">\n  <div class="logo">CRIPGOLD</div>\n'
        f'  <div class="logo-sub">Mercado del Oro &nbsp;·&nbsp; Dashboard Diario</div>\n'
        f'  <div class="hdr-date">📅 <b>{fecha}</b> &nbsp;·&nbsp; {now_str}</div>\n'
        f'  <div class="ticker">{ticker_html}</div>\n</div>\n\n'
        f'<div class="main">\n\n'
        f'<div class="dash-row">\n'
        f'<div class="dash-box">\n  <div class="dash-title">📊 Sentimiento del Mercado</div>\n'
        f'  <div class="sent-score">\n    <div class="sent-num" style="color:{sent_color};">{sent}</div>\n'
        f'    <div class="sent-lbl" style="color:{sent_color};">{sent_label}</div>\n  </div>\n'
        f'  <div class="gauge-track"><div class="gauge-needle" style="left:{sent}%;"></div></div>\n'
        f'  <div class="gauge-labels"><span>BAJISTA</span><span>NEUTRAL</span><span>ALCISTA</span></div>\n</div>\n'
        f'<div class="dash-box">\n  <div class="dash-title">📡 Indicadores de Mercado</div>\n'
        f'  {indicators_html}\n</div>\n</div>\n\n'
        f'<div class="sec-label">📰 Inteligencia de mercado &nbsp;·&nbsp; {len(arts)} artículos seleccionados</div>\n'
        f'<h2 class="sec-title">Noticias del Día por Categoría</h2>\n'
        f'{grupos_html}\n'
        f'<div class="ref-box">\n  <div class="ref-lbl">💡 Titular Destacado del Día</div>\n'
        f'  <p class="ref-text">{ref_text}</p>\n'
        f'  <span class="ref-src">— {ref_src} &nbsp;·&nbsp; Agente CripGold {fecha}</span>\n</div>\n\n'
        f'</div>\n\n'
        f'<div class="ftr">\n  Generado por <b>Agente CripGold V3.2</b> &nbsp;·&nbsp; {now_str}<br>\n'
        f'  Metales preciosos &nbsp;·&nbsp; Inversiones &nbsp;·&nbsp; Gemas &nbsp;·&nbsp; Colombia\n</div>\n\n'
        f'</body>\n</html>'
    )

    nombre_archivo = f"reporte_cripgold_{datetime.datetime.now().strftime('%Y%m%d')}.html"
    ruta = os.path.join(tempfile.gettempdir(), nombre_archivo)
    with open(ruta, 'w', encoding='utf-8') as fh:
        fh.write(html)

    print(f"[REPORTE] HTML generado: {ruta} ({os.path.getsize(ruta):,} bytes)")
    return ruta

# ============================================================
#   MAIN
# ============================================================
if __name__ == "__main__":
    fecha = datetime.datetime.now().strftime('%d/%m/%Y')
    print(f"\n{'='*50}")
    print(f"  AGENTE CRIPGOLD V3.2 — {fecha}")
    print(f"{'='*50}\n")

    enviar_telegram(f"🤖 <b>Agente CripGold V3.2 — Iniciado</b>\n📅 {fecha}")

    # Tarea 1: Precios
    oro_usd, usd_cop, gramo_cop, cambio_pct = tarea_precios(fecha)

    # Tarea 1B: Dashboard HTML de precios (uso interno CripGold)
    if gramo_cop:
        print("[DASHBOARD] Generando dashboard de precios...")
        generar_dashboard_precios_html(oro_usd, usd_cop, gramo_cop, cambio_pct, fecha)

    # Tarea 2: Noticias
    arts = tarea_noticias(fecha)

    # Tarea 3: Reporte HTML de noticias
    if arts:
        print("[REPORTE] Generando reporte HTML del día...")
        ruta_reporte = generar_reporte_html(arts, fecha, oro_usd, usd_cop)
        if ruta_reporte and os.path.exists(ruta_reporte):
            if oro_usd:
                caption = (
                    f"📊 <b>Reporte CripGold</b> · {fecha}\n"
                    f"📰 {len(arts)} noticias del mercado\n"
                    f"🥇 Oro: ${oro_usd:,.2f} USD/oz"
                )
            else:
                caption = (
                    f"📊 <b>Reporte CripGold</b> · {fecha}\n"
                    f"📰 {len(arts)} noticias seleccionadas"
                )
            enviar_documento_telegram(ruta_reporte, caption)
            print(f"[REPORTE] Enviado a {len(DESTINATARIOS)} destinatarios.")
    else:
        print("[REPORTE] Sin noticias — reporte HTML omitido.")

    enviar_telegram("✅ <b>Agente CripGold — Tareas completadas.</b>")
    print("\n[DONE] Agente V3.2 finalizado.")
