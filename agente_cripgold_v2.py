import requests
import datetime
import os
import time
# ============================================================
#   AGENTE CRIPGOLD V3 — Noticias por categoría + EN + LatAm
#   Sin Flask. Corre de arriba a abajo, luego termina.
# ============================================================

# --- CONFIGURACIÓN (en GitHub Actions van como Secrets) ---
TOKEN         = os.environ.get("TELEGRAM_TOKEN", "8678579635:AAFbm5FMzbuDKYCnL_ttmoI0Zq5_ytRrYYM")
DESTINATARIOS = os.environ.get("TELEGRAM_CHATS", "8526092375,5503549435,6915327599").split(",")
NEWS_KEY      = os.environ.get("NEWS_API_KEY", "600c50b8de384fa88ba678ab4724d738")

# ============================================================
#   UTILIDADES
# ============================================================
def enviar_telegram(texto):
    """Envía un mensaje a todos los destinatarios."""
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
    """Lleva un contador de envíos por tipo (precios / noticias)."""
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
    """Evita repetir noticias ya enviadas (guarda últimas 300)."""
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
    oro_usd = None
    try:
        url_gp = "https://data-asg.goldprice.org/dbXRates/USD"
        res_gp = requests.get(url_gp, headers=headers, timeout=12)
        if res_gp.status_code == 200:
            data_gp = res_gp.json()
            precio_gp = data_gp['items'][0]['xauPrice']
            if precio_gp and float(precio_gp) > 100:
                oro_usd = float(precio_gp)
                print(f"[PRECIOS] goldprice.org: ${oro_usd}")
    except Exception as e:
        print(f"[PRECIOS] goldprice.org falló: {e}")

    if not oro_usd:
        for ticker in ["XAUUSD=X", "GC=F"]:
            try:
                url_yf = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
                res_yf = requests.get(url_yf, headers=headers, timeout=12)
                if res_yf.status_code == 200:
                    precio_yf = res_yf.json()['chart']['result'][0]['meta']['regularMarketPrice']
                    if precio_yf and float(precio_yf) > 100:
                        oro_usd = float(precio_yf)
                        print(f"[PRECIOS] Yahoo Finance ({ticker}): ${oro_usd}")
                        break
            except:
                continue

    usd_cop = None
    try:
        url_cop = "https://query1.finance.yahoo.com/v8/finance/chart/COP=X?interval=1d&range=5d"
        res_cop = requests.get(url_cop, headers=headers, timeout=12)
        if res_cop.status_code == 200:
            usd_cop = float(res_cop.json()['chart']['result'][0]['meta']['regularMarketPrice'])
    except:
        pass

    if oro_usd and usd_cop:
        gramo_cop = (oro_usd / 31.1034768) * usd_cop
        return oro_usd, usd_cop, gramo_cop
    return None, None, None

def construir_mensaje_precios(base_gramo, porcentaje, folio, fecha):
    base     = base_gramo * porcentaje
    etiqueta = f"{int(porcentaje * 100)}%"
    def f(v):  return f"{int(v):,.0f}".replace(",", ".")
    def fr(v): return f"{int(round(v / 1000) * 1000):,.0f}".replace(",", ".")
    msg = (
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
    return msg

def tarea_precios(fecha):
    print("[PRECIOS] Iniciando...")
    oro_usd, usd_cop, gramo_cop = obtener_precio_oro_cop()
    if not gramo_cop:
        enviar_telegram(
            "⚠️ AGENTE CRIPGOLD — ERROR EN PRECIOS\n"
            "No se pudo obtener el precio del oro.\n"
            "Verifica manualmente en finance.yahoo.com"
        )
        return
    folio = gestionar_folio("precios")
    encabezado = (
        f"📊 <b>Mercado hoy:</b>\n"
        f"🥇 Oro: <b>${oro_usd:,.2f} USD/oz</b>\n"
        f"💵 TRM: <b>${usd_cop:,.2f} COP/USD</b>\n"
        f"⚖️ Gramo 24K: <b>${gramo_cop:,.0f} COP</b>"
    )
    enviar_telegram(encabezado)
    enviar_telegram(construir_mensaje_precios(gramo_cop, 0.83, folio, fecha))
    enviar_telegram(construir_mensaje_precios(gramo_cop, 0.84, folio, fecha))
    print(f"[PRECIOS] OK — gramo 24K: ${gramo_cop:,.0f} COP")

# ============================================================
#   TAREA 2 — NOTICIAS V3: CUBETAS POR CATEGORÍA
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
    "temporada de juego","pase de batalla",
    "lució","llevó puesto","vistió con","reina camilla","kate middleton",
    "meghan markle","alfombra roja","look de","outfit","tendencia de moda",
    "colección de joyas","joya real","novia real","boda real",
    "mar del plata","río de la plata",
    "estafa","robo de","hurto de","arrestaron","capturaron","secuestro",
    "fútbol","futbol","balón de oro","gol de oro","medalla de oro",
    "copa de oro","nba","nfl","champions","premier league","atletismo",
    "ciclismo","tenis","boxeo",
    "premio platino","premios platino","golden globe","bafta","emmy",
    "grammy","bts","kpop","concierto","gira musical",
    "actor","actriz","estreno de","película",
    "plazo fijo","cepo al dólar","dólar blue",
    "granos","soja","trigo","maíz","cosecha","ganadería",
    "samsung","xiaomi","iphone","receta","cocina","celular","smartphone",
    "corazón de oro","edad de oro","regla de oro","color dorado",
    "boda de plata","disco de oro",
]

CONTEXTO_ORO = [
    "precio del oro","cotización del oro","onza de oro","onza troy",
    "mercado del oro","reservas de oro","lingote de oro","lingotes de oro",
    "minería de oro","minería aurífera","oro físico","producción de oro",
    "inversión en oro","demanda de oro","activo de oro","fondo de oro",
    "etf de oro","futuros del oro","precio spot del oro","récord del oro",
    "máximo histórico del oro","repatriación de oro","minería ilegal de oro",
    "brics oro","bancos centrales oro","reserva en oro","banco central",
    "gold price","gold market","xau","gold rally","gold forecast",
    "gold reserve","gold mining","spot gold","troy ounce",
]

# ─────────────────────────────────────────────────────────────
#   CUBETAS: target = cuántas noticias queremos por categoría
# ─────────────────────────────────────────────────────────────
CATEGORIAS = {
    'oro': {
        'target': 7,
        'emoji': '🥇',
        'label': 'ORO',
        # Español — Colombia/LatAm primero, luego global
        'queries_es': [
            # 1. Colombia y LatAm local — PRIORIDAD MÁXIMA
            '(Colombia OR Medellín OR Bogotá OR Boyacá OR Antioquia OR Latinoamérica OR América Latina) AND ("oro" OR "minería aurífera" OR "producción de oro" OR "precio del oro")',
            # 2. Geopolítica global con impacto en oro
            '"oro" AND ("guerra" OR "aranceles" OR "Trump" OR "Irán" OR "tensión geopolítica" OR "repatriación" OR "crisis")',
            # 3. Bancos centrales y macroeconomía
            '"reservas de oro" OR "repatriación de oro" OR "banco central" AND "oro" OR "brics" AND "oro" OR "fondo de oro"',
            # 4. Precio y cotización
            '"precio del oro" OR "cotización del oro" OR "onza de oro" OR "XAU/USD" OR "precio spot del oro"',
            # 5. Minería e inversión
            '"producción de oro" OR "minería aurífera" OR "inversión en oro" OR "ETF de oro" OR "récord del oro"',
        ],
        # Inglés — cobertura internacional que no llega en español
        'queries_en': [
            # 6. Precio y análisis hoy
            '"gold price" OR "gold market" OR "XAU/USD" OR "spot gold"',
            # 7. Fed, inflación y macro
            '"gold" AND ("Federal Reserve" OR "Fed" OR "interest rates" OR "inflation" OR "recession")',
            # 8. Geopolítica en inglés
            '"gold" AND ("Iran" OR "war" OR "tariffs" OR "Trump" OR "geopolitical" OR "BRICS")',
            # 9. Analistas y pronósticos
            '"gold forecast" OR "gold outlook" OR "gold rally" OR "gold record" OR "gold all-time high"',
        ],
    },
    'plata': {
        'target': 1,
        'emoji': '🥈',
        'label': 'PLATA',
        'queries_es': [
            '"precio de la plata" OR "cotización de la plata" OR "mercado de la plata" OR "XAG/USD"',
            '"plata" AND ("análisis" OR "inversión" OR "rally" OR "récord" OR "caída" OR "mínimo" OR "máximo")',
        ],
        'queries_en': [
            '"silver price" OR "silver market" OR "XAG/USD" OR "silver forecast" OR "silver rally"',
            '"silver" AND ("Federal Reserve" OR "inflation" OR "gold ratio" OR "mining" OR "investment")',
        ],
    },
    'diamante': {
        'target': 1,
        'emoji': '💎',
        'label': 'DIAMANTES',
        'queries_es': [
            '"mercado de diamantes" OR "industria del diamante" OR "diamantes de laboratorio" OR "crisis del diamante" OR "mina de diamantes" OR "De Beers"',
            '"diamante" AND ("precio" OR "inversión" OR "sintético" OR "laboratorio" OR "cierre" OR "récord")',
        ],
        'queries_en': [
            '"diamond market" OR "diamond industry" OR "lab grown diamonds" OR "De Beers" OR "diamond mining"',
            '"diamond" AND ("price" OR "investment" OR "synthetic" OR "lab" OR "crisis" OR "Rio Tinto")',
        ],
    },
    'esmeralda': {
        'target': 1,
        'emoji': '💚',
        'label': 'ESMERALDAS',
        'queries_es': [
            '"esmeralda" OR "esmeraldas" OR "esmeraldas colombianas" OR "sector esmeraldero" OR "Fedesmeraldas" OR "muzo" OR "chivor" OR "marmato"',
            'Colombia AND ("esmeralda" OR "piedra preciosa" OR "gema" OR "exportación esmeraldas" OR "minería esmeraldas")',
        ],
        'queries_en': [
            '"Colombian emerald" OR "emerald market" OR "emerald mining" OR "emerald price" OR "precious stones Colombia"',
        ],
    },
}

# Configuración de locales para Google News RSS
LOCALES = {
    'es': {'hl': 'es-419', 'gl': 'CO', 'ceid': 'CO:es'},
    'en': {'hl': 'en-US',  'gl': 'US', 'ceid': 'US:en'},
}

def obtener_noticias():
    import xml.etree.ElementTree as ET
    import urllib.parse
    from email.utils import parsedate_to_datetime

    ahora    = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    hace_48h = ahora - datetime.timedelta(hours=48)

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    }

    resultados    = {cat: [] for cat in CATEGORIAS}
    titulos_vistos = set()

    def fetch_items(query, lang):
        """Llama a Google News RSS y devuelve los <item> encontrados."""
        loc = LOCALES[lang]
        q_enc = urllib.parse.quote(query)
        url   = (f"https://news.google.com/rss/search"
                 f"?q={q_enc}&hl={loc['hl']}&gl={loc['gl']}&ceid={loc['ceid']}")
        res  = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(res.content)
        return root.findall('.//item')

    def validar(item, categoria):
        """Devuelve (titulo, link) si pasa todos los filtros, si no None."""
        titulo   = (item.findtext('title')       or '').strip()
        link     = (item.findtext('link')        or '').strip()
        pub_date = (item.findtext('pubDate')     or '').strip()
        desc     = (item.findtext('description') or '').strip()

        if not titulo or not link:
            return None

        # Filtro 0 — fuente bloqueada
        src = item.find('source')
        if src is not None:
            fuente = ((src.text or '') + ' ' + (src.get('url') or '')).lower()
            if any(d in fuente for d in DOMINIOS_BLOQUEADOS_FUENTE):
                return None

        # Filtro 1 — ventana de 48 h
        try:
            if parsedate_to_datetime(pub_date) < hace_48h:
                return None
        except Exception:
            pass

        texto = (titulo + ' ' + desc).lower()

        # Filtro 2 — basura
        if any(b in texto for b in BASURA):
            return None

        # Filtro 3 — contexto de metales (solo para oro, las otras categorías
        #            tienen queries muy específicas que sirven de filtro)
        if categoria == 'oro' and not any(c in texto for c in CONTEXTO_ORO):
            return None

        # Filtro 4 — historial entre ejecuciones
        if gestionar_historial(titulo):
            return None

        # Filtro 5 — duplicados dentro de esta tanda
        clave = normalizar_titulo(titulo)
        if clave in titulos_vistos:
            return None

        return titulo, link

    # ── LLENADO DE CUBETAS ─────────────────────────────────────────────────
    for cat_name, cat in CATEGORIAS.items():
        target = cat['target']
        print(f"\n[NOTICIAS] ── {cat['emoji']} {cat['label']} (objetivo: {target}) ──")

        # Construir lista de (query, lang) priorizando español
        queries_a_probar = (
            [(q, 'es') for q in cat['queries_es']] +
            [(q, 'en') for q in cat['queries_en']]
        )

        for query, lang in queries_a_probar:
            if len(resultados[cat_name]) >= target:
                break
            try:
                items = fetch_items(query, lang)
                for item in items:
                    if len(resultados[cat_name]) >= target:
                        break
                    resultado = validar(item, cat_name)
                    if resultado:
                        titulo, link = resultado
                        titulos_vistos.add(normalizar_titulo(titulo))
                        resultados[cat_name].append({'title': titulo, 'url': link})
                        print(f"  ✓ [{lang.upper()}] {titulo[:70]}")
                time.sleep(0.8)
            except Exception as e:
                print(f"  [ERROR] {cat_name}/{lang}: {e}")

        encontradas = len(resultados[cat_name])
        estado      = "✅" if encontradas >= target else f"⚠️ ({encontradas}/{target})"
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
            "No se encontraron noticias nuevas en las últimas 48h.\n"
            "Puede ser un día sin novedades o un problema de conectividad."
        )
        print("[NOTICIAS] Sin resultados válidos hoy.")
        return

    folio   = gestionar_folio("noticias")
    msg     = (
        f"💎 <b>NOTICIAS — METALES Y GEMAS</b> 🏆\n"
        f"📅 <i>{fecha}    #{folio}</i>\n\n"
    )

    contador = 1
    for cat_name, cat in CATEGORIAS.items():
        arts = resultados[cat_name]
        if not arts:
            continue
        msg += f"{cat['emoji']} <b>{cat['label']}</b>\n"
        for art in arts:
            msg += f"<b>{contador}.</b> <a href='{art['url']}'>{art['title']}</a>\n"
            contador += 1
        msg += "\n"

    msg += f"🤖 <i>Agente CripGold — Investigación finalizada.</i>"
    enviar_telegram(msg)
    print(f"[NOTICIAS] OK — {total} noticias enviadas.")

# ============================================================
#   MAIN
# ============================================================
if __name__ == "__main__":
    fecha = datetime.datetime.now().strftime('%d/%m/%Y')
    print(f"\n{'='*50}")
    print(f"  AGENTE CRIPGOLD V3 — {fecha}")
    print(f"{'='*50}\n")

    enviar_telegram(f"🤖 <b>Agente CripGold V3 — Iniciado</b>\n📅 {fecha}")

    tarea_precios(fecha)
    tarea_noticias(fecha)

    enviar_telegram("✅ <b>Agente CripGold — Tareas completadas.</b>")
    print("\n[DONE] Agente V3 finalizado correctamente.")
