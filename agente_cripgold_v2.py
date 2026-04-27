import requests
import datetime
import os
import time

# =====================================================================
#   AGENTE CRIPGOLD V2 — GitHub Actions Edition
#   Sin Flask. Corre de arriba a abajo, luego termina.
# =====================================================================

# --- CONFIGURACIÓN (en GitHub Actions van como Secrets) ---
TOKEN        = os.environ.get("TELEGRAM_TOKEN", "8678579635:AAFbm5FMzbуDKYCnL_ttmoI0Zq5_ytRrYYM")
DESTINATARIOS = os.environ.get("TELEGRAM_CHATS", "8526092375,5503549435,6915327599").split(",")
NEWS_KEY     = os.environ.get("NEWS_API_KEY", "600c50b8de384fa88ba678ab4724d738")

# =====================================================================
#   UTILIDADES
# =====================================================================

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


def enviar_documento_telegram(ruta_archivo, caption=""):
    """Envía un archivo como documento a todos los destinatarios via Telegram."""
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
        return True  # ya fue enviada

    historial.append(clave)
    try:
        with open(archivo, "w") as f:
            f.write("\n".join(historial[-300:]))
    except:
        pass
    return False


# =====================================================================
#   TAREA 1 — PRECIOS DE COMPRA CRIPGOLD
# =====================================================================

def obtener_precio_oro_cop():
    """
    Obtiene el precio spot del oro en USD desde goldprice.org (misma fuente
    que usa Thomas manualmente) y lo convierte a COP con la TRM de Yahoo Finance.
    """
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/json'
    }

    oro_usd = None

    # FUENTE 1: goldprice.org — misma fuente que usa Thomas manualmente
    try:
        url_gp = "https://data-asg.goldprice.org/dbXRates/USD"
        res_gp = requests.get(url_gp, headers=headers, timeout=12)
        if res_gp.status_code == 200:
            data_gp = res_gp.json()
            precio_gp = data_gp['items'][0]['xauPrice']
            if precio_gp and float(precio_gp) > 100:
                oro_usd = float(precio_gp)
                print(f"[PRECIOS] Precio obtenido desde goldprice.org: ${oro_usd}")
    except Exception as e:
        print(f"[PRECIOS] goldprice.org falló: {e}")

    # FUENTE 2: Yahoo Finance como respaldo si goldprice.org no responde
    if not oro_usd:
        for ticker in ["XAUUSD=X", "GC=F"]:
            try:
                url_yf = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
                res_yf = requests.get(url_yf, headers=headers, timeout=12)
                if res_yf.status_code == 200:
                    precio_yf = res_yf.json()['chart']['result'][0]['meta']['regularMarketPrice']
                    if precio_yf and float(precio_yf) > 100:
                        oro_usd = float(precio_yf)
                        print(f"[PRECIOS] Precio obtenido desde Yahoo Finance ({ticker}): ${oro_usd}")
                        break
            except:
                continue

    # TRM: USD a COP desde Yahoo Finance
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
    """
    Genera el bloque de texto de precios para un porcentaje dado.
    porcentaje: 0.83 o 0.84
    """
    base = base_gramo * porcentaje
    etiqueta = f"{int(porcentaje * 100)}%"

    def f(v):
        return f"{int(v):,.0f}".replace(",", ".")

    def fr(v):
        return f"{int(round(v / 1000) * 1000):,.0f}".replace(",", ".")

    msg = (
        f"💰 <b>PRECIOS DE COMPRA CRIPGOLD</b> 💰\n"
        f"📅 <i>{fecha}    #{folio} — Base {etiqueta}</i>\n"
        f"❖❖❖❖❖❖❖❖❖❖\n\n"
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
        f"❖❖❖❖❖❖❖❖❖❖"
    )
    return msg


def tarea_precios(fecha):
    print("[PRECIOS] Iniciando...")
    oro_usd, usd_cop, gramo_cop = obtener_precio_oro_cop()

    if not gramo_cop:
        enviar_telegram(
            "⚠️ AGENTE CRIPGOLD — ERROR EN PRECIOS\n"
            "No se pudo obtener el precio del oro desde las fuentes.\n"
            "Verifica manualmente en finance.yahoo.com"
        )
        print("[PRECIOS] ERROR: no se obtuvo precio.")
        return None, None, None

    folio = gestionar_folio("precios")

    # Encabezado con datos de mercado
    encabezado = (
        f"📊 <b>Mercado hoy:</b>\n"
        f"🥇 Oro: <b>${oro_usd:,.2f} USD/oz</b>\n"
        f"💵 TRM: <b>${usd_cop:,.2f} COP/USD</b>\n"
        f"⚡️ Gramo 24K: <b>${gramo_cop:,.0f} COP</b>"
    )
    enviar_telegram(encabezado)

    # Tanda 1 — Base al 83%
    msg_83 = construir_mensaje_precios(gramo_cop, 0.83, folio, fecha)
    enviar_telegram(msg_83)

    # Tanda 2 — Base al 84%
    msg_84 = construir_mensaje_precios(gramo_cop, 0.84, folio, fecha)
    enviar_telegram(msg_84)

    print(f"[PRECIOS] OK — gramo 24K: ${gramo_cop:,.0f} COP")
    return oro_usd, usd_cop, gramo_cop


# =====================================================================
#   TAREA 2 — NOTICIAS MERCADO DE METALES Y GEMAS
# =====================================================================

def normalizar_titulo(titulo):
    """
    Normaliza un titulo para detectar duplicados:
    - Elimina fechas y dias de la semana
    - Elimina palabras muy comunes (stopwords)
    - Devuelve las primeras palabras clave para comparar
    """
    import re
    STOPWORDS = {
        'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'en', 'y', 'a',
        'que', 'con', 'por', 'para', 'se', 'su', 'sus', 'al', 'es', 'son',
        'ha', 'han', 'le', 'lo', 'todo', 'toda', 'este', 'esta', 'como',
        'pero', 'mas', 'muy', 'ya', 'si', 'no', 'o', 'e', 'ni', 'sobre',
        'entre', 'tras', 'ante', 'bajo', 'desde', 'hasta', 'hacia', 'sin',
        'por', 'pro', 'vs'
    }
    t = titulo.lower()
    # Quitar fechas y dias
    t = re.sub(r'\d{1,2} de \w+ de \d{4}', '', t)
    t = re.sub(r'(lunes|martes|miercoles|jueves|viernes|sabado|domingo)', '', t)
    t = re.sub(r'\d+', '', t)
    # Quitar puntuacion
    t = re.sub(r'[^\w\s]', ' ', t)
    # Filtrar stopwords y tomar las primeras 6 palabras clave
    palabras = [p for p in t.split() if p not in STOPWORDS and len(p) > 3]
    return ' '.join(palabras[:6])


# ── DOMINIOS BLOQUEADOS — se verifican en el elemento <source> del RSS ──────
# Vietnam.vn, por ejemplo, publica diario precios del oro en VND que no
# son relevantes para Colombia aunque el título parezca legítimo.
DOMINIOS_BLOQUEADOS_FUENTE = [
    "vietnam.vn",
    "vietstock.vn",
    "vnexpress",
    "thanhnien",
    "tuoitre",
    "baodautu",
    "cafef.vn",
    "tinnhanhchungkhoan",
]


def obtener_noticias():
    """
    Obtiene noticias desde Google News RSS — gratis, sin API key,
    con la misma cobertura que una búsqueda manual en Google.
    """
    import xml.etree.ElementTree as ET
    import urllib.parse
    from email.utils import parsedate_to_datetime

    ahora = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    # Ventana de 48h para capturar más artículos (36h era muy estricto)
    hace_48h = ahora - datetime.timedelta(hours=48)

    # ── CONTEXTO OBLIGATORIO ─────────────────────────────────────────────────
    # Al menos UNA de estas frases debe aparecer en titulo+descripcion.
    CONTEXTO_MERCADO = [
        # Oro — precio y mercado
        "precio del oro", "cotización del oro", "onza de oro", "onza troy",
        "mercado del oro", "reservas de oro", "lingote de oro", "lingotes de oro",
        "minería de oro", "minería aurífera", "oro físico", "producción de oro",
        "extracción de oro", "comercio de oro", "compra de oro",
        "inversión en oro", "demanda de oro", "activo de oro",
        "fondo de oro", "etf de oro", "futuros del oro", "precio spot del oro",
        "récord del oro", "máximo histórico del oro", "repatriación de oro",
        "minería ilegal de oro", "formalización minera", "ecoDorado",
        "compañía minera de oro", "producción aurífera",
        # Plata, platino, paladio
        "precio de la plata", "cotización de la plata", "onza de plata",
        "mercado de la plata", "lingote de plata", "inversión en plata",
        "precio del platino", "precio del paladio", "paladio",
        # Metales preciosos en general
        "metales preciosos", "metal precioso", "activo refugio",
        "valor refugio", "refugio de valor", "centenario de oro",
        # Geopolítica con metales
        "brics oro", "bancos centrales oro", "reserva en oro",
        "banco central compra oro", "reservas de oro de los bancos",
        # Esmeraldas y gemas
        "esmeralda", "esmeraldas", "esmeraldas colombianas",
        "muzo", "marmato", "chivor", "minería de esmeraldas",
        "piedra preciosa", "piedras preciosas",
        # Diamantes
        "industria del diamante", "mercado de diamantes", "mina de diamantes",
        "diamantes sintéticos", "diamantes de laboratorio", "producción de diamantes",
        "crisis del diamante", "comercio de diamantes",
    ]

    # ── BASURA — ELIMINACIÓN INMEDIATA ──────────────────────────────────────
    BASURA = [
        # Vietnam: palabras específicas de sus reportes de precio local
        "precio del oro en sjc",
        "anillos de oro de 9999",
        "precio del oro en vietnam",
        "precio mundial del oro. - vietnam",
        "vnd por onza",
        "sjc, precio del oro",
        "precio del oro de 24 quilates y precios mundiales",
        "tael de oro",
        # Videojuegos
        "free fire", "freefire", "códigos de hoy", "recompensas gratis",
        "league of legends", "clash of clans", "clash royale", "fortnite",
        "valorant", "pubg", "mobile legends", "honor of kings",
        "battle royale", "videojuego", "gaming", "gamer", "gameplay",
        "rango de oro", "rango de plata", "rango de diamante",
        "temporada de juego", "pase de batalla", "loot",
        # Moda y farándula
        "lució", "llevó puesto", "vistió con",
        "reina camilla", "kate middleton", "meghan markle",
        "alfombra roja", "look de", "outfit", "tendencia de moda",
        "diseño de joyas", "colección de joyas", "joya real",
        "novia real", "boda real",
        # Geografía (ciudades con nombre de metal)
        "mar del plata", "río de la plata",
        # Crimen
        "estafa", "robo de", "hurto de", "arrestaron", "capturaron",
        "secuestro", "homicidio",
        # Deportes
        "fútbol", "futbol", "balón de oro", "gol de oro",
        "medalla de oro", "copa de oro", "nba", "nfl", "champions",
        "premier league", "atletismo", "ciclismo", "tenis", "boxeo",
        # Entretenimiento
        "premio platino", "premios platino",
        "golden globe", "bafta", "emmy", "grammy", "bts", "kpop",
        "concierto", "gira musical", "festival de cine",
        "actor", "actriz", "estreno de", "película",
        # Economía no relacionada
        "plazo fijo", "cepo al dólar", "dólar blue",
        "granos", "soja", "trigo", "maíz", "cosecha", "ganadería",
        "billete", "papel moneda", "tarjeta de crédito",
        # Tecnología / otros
        "samsung", "xiaomi", "iphone", "receta", "cocina",
        "celular", "smartphone", "biblioteca",
        # Metáforas
        "corazón de oro", "edad de oro", "regla de oro",
        "color dorado", "boda de plata", "disco de oro",
    ]

    noticias_validas = []
    titulos_vistos  = set()

    # ── CONSULTAS TEMÁTICAS — MAX 3 ARTÍCULOS POR TEMA ─────────────────────
    # Cada tupla: (query, max_articulos_por_consulta)
    CONSULTAS = [
        # TEMA 1: Geopolítica y guerra — cómo afectan al oro en el mundo
        ('"oro" AND ("guerra" OR "aranceles" OR "Trump" OR "geopolítica" OR '
         '"Oriente Medio" OR "misil" OR "tensión" OR "repatriación")', 3),

        # TEMA 2: Bancos centrales, BRICS, reservas — tendencias macro globales
        ('"reservas de oro" OR "repatriación de oro" OR "bancos centrales" AND "oro" '
         'OR "brics" AND "oro" OR "lingote de oro" OR "banco central" AND "oro"', 3),

        # TEMA 3: Colombia local — Medellín, minería, esmeraldas, regulación
        ('(Colombia OR Medellín OR Bogotá OR Boyacá OR Antioquia) AND '
         '("oro" OR "esmeraldas" OR "minería" OR "muzo" OR "marmato" OR "chivor")', 3),

        # TEMA 4: Cotización y precio — solo 2, no saturar
        ('"precio del oro" OR "cotización del oro" OR "precio de la plata" '
         'OR "cotización de la plata" OR "onza de oro"', 2),

        # TEMA 5: Diamantes — crisis, laboratorio, cierre de minas
        ('"industria del diamante" OR "diamantes de laboratorio" OR '
         '"diamantes sintéticos" OR "crisis del diamante" OR "mina de diamantes"', 2),

        # TEMA 6: Plata, platino, paladio — mercado e inversión
        ('"mercado de la plata" OR "precio de la plata" OR "platino" OR "paladio" '
         'OR "metales preciosos" AND ("inversión" OR "refugio" OR "rally" OR "récord")', 2),

        # TEMA 7: Minería global — récords, grandes empresas, África, Asia
        ('"producción de oro" AND ("récord" OR "record") OR '
         '"compañía minera" AND "oro" OR "Zimbabue" AND "oro" OR '
         '"Singapur" AND "oro" OR "minería aurífera" AND ("récord" OR "record")', 2),

        # TEMA 8 (RESCATE): consulta amplia si no llegamos a 8 artículos
        # Se activa automáticamente si los temas anteriores no alcanzan.
        ('"oro" OR "plata" OR "metales preciosos" OR "esmeraldas"', 3),
    ]

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    }

    for i_consulta, (query, max_por_consulta) in enumerate(CONSULTAS):
        if len(noticias_validas) >= 10:
            break

        # El tema 8 (rescate) solo corre si tenemos menos de 8 artículos
        if i_consulta == 7 and len(noticias_validas) >= 8:
            break

        encontrados_esta_consulta = 0
        try:
            q_encoded = urllib.parse.quote(query)
            url_rss = (
                f"https://news.google.com/rss/search"
                f"?q={q_encoded}&hl=es-419&gl=CO&ceid=CO:es"
            )
            res  = requests.get(url_rss, headers=headers, timeout=15)
            root = ET.fromstring(res.content)

            for item in root.findall('.//item'):
                if len(noticias_validas) >= 10:
                    break
                if encontrados_esta_consulta >= max_por_consulta:
                    break

                titulo   = (item.findtext('title') or "").strip()
                link     = (item.findtext('link') or "").strip()
                pub_date = (item.findtext('pubDate') or "").strip()
                desc     = (item.findtext('description') or "").strip()

                if not titulo or not link:
                    continue

                # FILTRO 0: Bloquear fuentes vietnamitas (y similares) por source element
                source_elem = item.find('source')
                if source_elem is not None:
                    fuente_nombre = (source_elem.text or "").lower()
                    fuente_url    = (source_elem.get('url') or "").lower()
                    fuente_completa = fuente_nombre + " " + fuente_url
                    if any(d in fuente_completa for d in DOMINIOS_BLOQUEADOS_FUENTE):
                        print(f"[NOTICIAS] Fuente bloqueada ({fuente_nombre}): {titulo[:50]}")
                        continue

                # FILTRO 1: solo noticias de las ultimas 48h
                try:
                    fecha_pub = parsedate_to_datetime(pub_date)
                    if fecha_pub < hace_48h:
                        continue
                except Exception:
                    pass  # si no se parsea la fecha, se incluye igual

                texto_check = (titulo + " " + desc).lower()

                # FILTRO 2: basura fuera (Vietnam local, juegos, moda, deporte)
                if any(b in texto_check for b in BASURA):
                    continue

                # FILTRO 3: debe tener contexto real de metales/gemas
                if not any(c in texto_check for c in CONTEXTO_MERCADO):
                    continue

                # FILTRO 4: sin repetidos historicos entre ejecuciones
                if gestionar_historial(titulo):
                    continue

                # FILTRO 5: sin duplicados en esta tanda (misma historia, distinta fuente)
                clave = normalizar_titulo(titulo)
                if clave in titulos_vistos:
                    continue
                titulos_vistos.add(clave)

                noticias_validas.append({'title': titulo, 'url': link})
                encontrados_esta_consulta += 1
                print(f"[NOTICIAS] T{i_consulta+1} [{encontrados_esta_consulta}/{max_por_consulta}] {titulo[:65]}")

        except Exception as e:
            print(f"[NOTICIAS] Error en consulta {i_consulta+1}: {e}")

        # Pequeña pausa entre consultas para no saturar Google
        time.sleep(1)

    print(f"[NOTICIAS] Total encontradas: {len(noticias_validas)}")
    return noticias_validas


def tarea_noticias(fecha):
    print("[NOTICIAS] Iniciando...")
    arts = obtener_noticias()

    if not arts:
        enviar_telegram(
            "⚠️ <b>AGENTE CRIPGOLD — SIN NOTICIAS</b>\n"
            "No se encontraron noticias nuevas sobre metales y gemas en las ultimas 48h.\n"
            "Puede ser un dia sin novedades o un problema de conectividad."
        )
        print("[NOTICIAS] Sin resultados válidos hoy.")
        return []

    folio = gestionar_folio("noticias")
    msg = (
        f"📎 <b>NOTICIAS — METALES Y GEMAS</b> 🏆\n"
        f"📅 <i>{fecha}    #{folio}</i>\n\n"
    )
    for i, art in enumerate(arts, 1):
        msg += f"<b>{i}.</b> <a href='{art['url']}'>{art['title']}</a>\n"

    msg += "\n🧬 <i>Agente CripGold — Investigación finalizada.</i>"
    enviar_telegram(msg)
    print(f"[NOTICIAS] OK — {len(arts)} noticias enviadas.")
    return arts


# =====================================================================
#   TAREA 3 — REPORTE HTML DIARIO
# =====================================================================

def generar_reporte_html(arts, fecha, oro_usd=None, usd_cop=None):
    """
    Genera el reporte HTML diario con las noticias del día y precios actuales.
    Devuelve la ruta al archivo generado.
    """
    import tempfile

    # --- Bloque de precios (opcional, si se obtuvo precio) ---
    if oro_usd and usd_cop:
        gramo_24k = (oro_usd / 31.1034768) * usd_cop
        precio_html = f"""
        <div class="precio-bar">
            <div class="precio-item">
                <span class="precio-label">🥇 ORO SPOT</span>
                <span class="precio-val">${oro_usd:,.2f} <small>USD/oz</small></span>
            </div>
            <div class="precio-divider"></div>
            <div class="precio-item">
                <span class="precio-label">💱 TRM HOY</span>
                <span class="precio-val">${usd_cop:,.2f} <small>COP/USD</small></span>
            </div>
            <div class="precio-divider"></div>
            <div class="precio-item">
                <span class="precio-label">⚡ GRAMO 24K</span>
                <span class="precio-val">${gramo_24k:,.0f} <small>COP</small></span>
            </div>
        </div>
        """
    else:
        precio_html = '<div class="precio-bar"><span style="color:#B8860B;">Precios no disponibles hoy</span></div>'

    # --- Tarjetas de noticias ---
    cards_html = ""
    for i, art in enumerate(arts, 1):
        cards_html += f"""
        <div class="card">
            <div class="card-num">{i:02d}</div>
            <div class="card-body">
                <a href="{art['url']}" class="card-title" target="_blank">{art['title']}</a>
            </div>
            <div class="card-arrow">→</div>
        </div>
        """

    # --- Timestamp ---
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CripGold · Reporte {fecha}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --gold: #FFD700;
    --gold-dark: #B8860B;
    --gold-dim: #7a6000;
    --bg: #0D0D0D;
    --bg2: #141414;
    --bg3: #1A1A1A;
    --text: #E8E8E8;
    --text-dim: #888;
    --border: rgba(255,215,0,0.15);
    --card-bg: rgba(255,215,0,0.04);
    --card-hover: rgba(255,215,0,0.08);
  }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
    padding: 0;
  }}

  /* ── HEADER ── */
  .header {{
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1400 50%, #0a0a0a 100%);
    border-bottom: 1px solid var(--border);
    padding: 40px 32px 28px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse 60% 80% at 50% 0%, rgba(255,215,0,0.06) 0%, transparent 70%);
    pointer-events: none;
  }}
  .logo-text {{
    font-family: 'Playfair Display', serif;
    font-size: 42px;
    font-weight: 900;
    letter-spacing: 6px;
    background: linear-gradient(135deg, #FFD700, #FFF8DC, #B8860B);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
  }}
  .logo-sub {{
    font-size: 11px;
    letter-spacing: 4px;
    color: var(--gold-dim);
    margin-top: 6px;
    text-transform: uppercase;
  }}
  .header-date {{
    margin-top: 16px;
    font-size: 13px;
    color: var(--text-dim);
    letter-spacing: 2px;
  }}
  .header-date strong {{ color: var(--gold); }}

  /* ── PRECIO BAR ── */
  .precio-bar {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0;
    background: rgba(255,215,0,0.05);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin: 28px auto 0;
    max-width: 700px;
    padding: 18px 24px;
    flex-wrap: wrap;
    gap: 12px;
  }}
  .precio-item {{
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    min-width: 140px;
  }}
  .precio-label {{
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--gold-dim);
    text-transform: uppercase;
    margin-bottom: 4px;
  }}
  .precio-val {{
    font-size: 20px;
    font-weight: 600;
    color: var(--gold);
  }}
  .precio-val small {{ font-size: 11px; color: var(--gold-dim); margin-left: 2px; }}
  .precio-divider {{
    width: 1px;
    height: 40px;
    background: var(--border);
    flex-shrink: 0;
  }}

  /* ── MAIN ── */
  .main {{
    max-width: 820px;
    margin: 0 auto;
    padding: 40px 24px 60px;
  }}

  .section-label {{
    font-size: 10px;
    letter-spacing: 4px;
    color: var(--gold-dark);
    text-transform: uppercase;
    margin-bottom: 6px;
  }}
  .section-title {{
    font-family: 'Playfair Display', serif;
    font-size: 26px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 24px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
  }}

  /* ── CARDS ── */
  .cards {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .card {{
    display: flex;
    align-items: center;
    gap: 16px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
    transition: background 0.2s, border-color 0.2s, transform 0.15s;
    cursor: pointer;
    text-decoration: none;
  }}
  .card:hover {{
    background: var(--card-hover);
    border-color: rgba(255,215,0,0.30);
    transform: translateX(4px);
  }}
  .card-num {{
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 900;
    color: var(--gold-dark);
    min-width: 36px;
    line-height: 1;
    opacity: 0.7;
  }}
  .card-body {{ flex: 1; }}
  .card-title {{
    font-size: 15px;
    font-weight: 500;
    color: var(--text);
    line-height: 1.45;
    text-decoration: none;
    display: block;
  }}
  .card-title:hover {{ color: var(--gold); }}
  .card-arrow {{
    font-size: 18px;
    color: var(--gold-dark);
    opacity: 0.5;
    flex-shrink: 0;
    transition: opacity 0.2s;
  }}
  .card:hover .card-arrow {{ opacity: 1; color: var(--gold); }}

  /* ── FOOTER ── */
  .footer {{
    text-align: center;
    padding: 32px 24px;
    border-top: 1px solid var(--border);
    color: var(--text-dim);
    font-size: 12px;
    letter-spacing: 1px;
  }}
  .footer strong {{ color: var(--gold-dark); }}

  /* ── SCANLINE DECO ── */
  body::after {{
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,0,0,0.03) 2px,
      rgba(0,0,0,0.03) 4px
    );
    pointer-events: none;
    z-index: 999;
  }}
</style>
</head>
<body>

<div class="header">
  <div class="logo-text">CRIPGOLD</div>
  <div class="logo-sub">Mercado del Oro · Análisis Diario</div>
  <div class="header-date">📅 <strong>{fecha}</strong> &nbsp;·&nbsp; Generado a las {now_str}</div>
  {precio_html}
</div>

<div class="main">
  <div class="section-label">📰 Inteligencia de mercado</div>
  <h2 class="section-title">Noticias del Día — {len(arts)} artículos seleccionados</h2>

  <div class="cards">
    {cards_html}
  </div>
</div>

<div class="footer">
  Generado automáticamente por <strong>Agente CripGold V2</strong> · {now_str}<br>
  Metales preciosos · Inversiones · Gemas · Colombia
</div>

</body>
</html>"""

    # Guardar en carpeta temporal del sistema
    nombre_archivo = f"reporte_cripgold_{datetime.datetime.now().strftime('%Y%m%d')}.html"
    ruta = os.path.join(tempfile.gettempdir(), nombre_archivo)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[REPORTE] HTML generado: {ruta} ({os.path.getsize(ruta):,} bytes)")
    return ruta


# =====================================================================
#   MAIN — Punto de entrada
# =====================================================================

if __name__ == "__main__":
    fecha = datetime.datetime.now().strftime('%d/%m/%Y')
    print(f"\n{'='*50}")
    print(f"  AGENTE CRIPGOLD V2 — {fecha}")
    print(f"{'='*50}\n")

    # Aviso de inicio
    enviar_telegram(f"🧬 <b>Agente CripGold V2 — Iniciado</b>\n📅 {fecha}")

    # Tarea 1: Precios (ahora retorna valores para el reporte)
    oro_usd, usd_cop, gramo_cop = tarea_precios(fecha)

    # Tarea 2: Noticias (ahora retorna la lista de artículos)
    arts = tarea_noticias(fecha)

    # Tarea 3: Reporte HTML — se genera y envía como documento Telegram
    if arts:
        print("[REPORTE] Generando reporte HTML del día...")
        ruta_reporte = generar_reporte_html(arts, fecha, oro_usd, usd_cop)
        if ruta_reporte and os.path.exists(ruta_reporte):
            caption = (
                f"📊 <b>Reporte CripGold</b> · {fecha}\n"
                f"📰 {len(arts)} noticias del mercado del oro\n"
                f"🥇 Oro: ${oro_usd:,.2f} USD/oz" if oro_usd else
                f"📊 <b>Reporte CripGold</b> · {fecha}\n📰 {len(arts)} noticias seleccionadas"
            )
            enviar_documento_telegram(ruta_reporte, caption)
            print(f"[REPORTE] Reporte enviado a {len(DESTINATARIOS)} destinatarios.")
        else:
            print("[REPORTE] ERROR: no se pudo generar el archivo HTML.")
    else:
        print("[REPORTE] Sin artículos — no se genera reporte hoy.")

    # Aviso de cierre
    enviar_telegram("✅ <b>Agente CripGold — Tareas completadas.</b>")
    print("\n[DONE] Agente finalizado correctamente.")
