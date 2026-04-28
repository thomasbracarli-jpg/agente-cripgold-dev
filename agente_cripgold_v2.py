import requests
import datetime
import os
import time
# ============================================================
#   AGENTE CRIPGOLD V3.2 — Búsquedas ampliadas:
#   plata x2, diamantes x2, esmeraldas con minas,
#   LatAm extendido, bancos centrales por país
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

    # Yahoo Finance — precio actual + cierre anterior
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
        return
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
    print(f"[PRECIOS] OK — gramo 24K: ${fmt_cop(gramo_cop)} COP")

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
        'queries': [
            '(Colombia OR Medellín OR Bogotá OR Boyacá OR Antioquia OR Venezuela OR Perú OR México OR Argentina OR Ecuador OR Chile OR Bolivia OR Uruguay OR Brasil) AND ("oro" OR "minería aurífera" OR "producción de oro" OR "reservas de oro")',
            '("oro" OR "minería de oro") AND (Colombia OR "BanRep" OR "Banco de la República" OR "Minhacienda" OR "ANM")',
            '("banco central" OR "reservas internacionales") AND "oro" AND (Colombia OR Venezuela OR Perú OR México OR Argentina OR Ecuador OR Chile OR Bolivia)',
            '"oro" AND ("guerra" OR "aranceles" OR "Trump" OR "Irán" OR "tensión" OR "repatriación" OR "sanciones" OR "Oriente Medio" OR "OPEP" OR "estrecho de Ormuz")',
            '"reservas de oro" OR "repatriación de oro" OR ("banco central" AND "oro") OR ("brics" AND "oro") OR "lingote de oro" OR ("Turquía" AND "oro") OR ("China" AND "reservas de oro")',
            '"precio del oro" AND
