import requests
import datetime
import os

# ============================================================
#   AGENTE CRIPGOLD V2 — GitHub Actions Edition
#   Sin Flask. Corre de arriba a abajo, luego termina.
# ============================================================

# --- CONFIGURACIÓN (en GitHub Actions van como Secrets) ---
TOKEN        = os.environ.get("TELEGRAM_TOKEN", "8678579635:AAFbm5FMzbuDKYCnL_ttmoI0Zq5_ytRrYYM")
DESTINATARIOS = os.environ.get("TELEGRAM_CHATS", "8526092375,5503549435,6915327599").split(",")
NEWS_KEY     = os.environ.get("NEWS_API_KEY", "600c50b8de384fa88ba678ab4724d738")

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
        return True  # ya fue enviada

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
            "⚠️ <b>AGENTE CRIPGOLD — ERROR EN PRECIOS</b>\n"
            "No se pudo obtener el precio del oro desde Yahoo Finance.\n"
            "Verifica manualmente: <a href='https://finance.yahoo.com/quote/GC%3DF/'>Yahoo Finance Oro</a>"
        )
        print("[PRECIOS] ERROR: no se obtuvo precio.")
        return

    folio = gestionar_folio("precios")

    # Encabezado con datos de mercado
    encabezado = (
        f"📊 <b>Mercado hoy:</b>\n"
        f"🥇 Oro: <b>${oro_usd:,.2f} USD/oz</b>\n"
        f"💵 TRM: <b>${usd_cop:,.2f} COP/USD</b>\n"
        f"⚖️ Gramo 24K: <b>${gramo_cop:,.0f} COP</b>"
    )
    enviar_telegram(encabezado)

    # Tanda 1 — Base al 83%
    msg_83 = construir_mensaje_precios(gramo_cop, 0.83, folio, fecha)
    enviar_telegram(msg_83)

    # Tanda 2 — Base al 84%
    msg_84 = construir_mensaje_precios(gramo_cop, 0.84, folio, fecha)
    enviar_telegram(msg_84)

    print(f"[PRECIOS] OK — gramo 24K: ${gramo_cop:,.0f} COP")


# ============================================================
#   TAREA 2 — NOTICIAS MERCADO DE METALES Y GEMAS
# ============================================================

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

def obtener_noticias():
    """
    Obtiene noticias desde Google News RSS — gratis, sin API key,
    con la misma cobertura que una búsqueda manual en Google.
    """
    import xml.etree.ElementTree as ET
    import urllib.parse
    from email.utils import parsedate_to_datetime

    ahora = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    hace_36h = ahora - datetime.timedelta(hours=36)

    # ── CONTEXTO OBLIGATORIO ─────────────────────────────────────────────────
    # Al menos UNA de estas frases debe aparecer en titulo+descripcion.
    # Son lo suficientemente especificas para no dejar pasar deportes o farándula.
    CONTEXTO_MERCADO = [
        # Oro — precio y mercado
        "precio del oro", "cotización del oro", "onza de oro", "onza troy",
        "mercado del oro", "reservas de oro", "lingote de oro", "lingotes de oro",
        "minería de oro", "minería aurífera", "oro físico", "producción de oro",
        "extracción de oro", "comercio de oro", "compra de oro",
        "inversión en oro", "demanda de oro", "activo de oro",
        "fondo de oro", "etf de oro", "futuros del oro", "precio spot del oro",
        "récord del oro", "máximo histórico del oro", "repatriación de oro",
        "minería ilegal de oro", "formalización minera", "ecodorado",
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

    # ── BASURA — ELIMINACIÓN INMEDIATA ───────────────────────────────────────
    BASURA = [
        # Vietnam: publica diario "precio del oro en SJC" — irrelevante para Colombia
        "precio del oro en sjc", "precio de las joyas de oro de 24k",
        "anillos de oro de 9999", "precio del oro en vietnam",
        "precio mundial del oro. - vietnam", "vnd por onza",
        "sjc, precio del oro", "precio del oro de 24 quilates y precios mundiales",
        # Videojuegos
        "free fire", "freefire", "códigos de hoy", "recompensas gratis",
        "league of legends", "clash of clans", "clash royale", "fortnite",
        "valorant", "pubg", "mobile legends", "honor of kings",
        "battle royale", "videojuego", "gaming", "gamer", "gameplay",
        "rango de oro", "rango de plata", "rango de diamante",
        "temporada de juego", "pase de batalla", "loot",
        # Moda y farándula
        "broche de diamante", "collar de diamante", "pulsera de oro",
        "anillo de oro", "joyería de moda", "bisutería",
        "lució", "llevó puesto", "vistió con",
        "reina camilla", "kate middleton", "meghan markle",
        "alfombra roja", "look de", "outfit", "tendencia de moda",
        "diseño de joyas", "colección de joyas", "joya real",
        "novia real", "boda real",
        # Geografía (ciudades con nombre de metal)
        "mar del plata", "río de la plata",
        # Crimen
        "estafa", "robo", "hurto", "murió", "falleció",
        "arrestó", "capturó", "secuestro", "homicidio", "asesinó", "víctima",
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

    # ── CONSULTAS TEMÁTICAS — MAX 2 ARTÍCULOS POR TEMA ────────────────────
    # Cada tupla: (query, max_articulos_por_consulta)
    # Esto garantiza DIVERSIDAD: geopolítica, Colombia local, mercado global,
    # diamantes, plata/platino, minería récord — nunca todo de un solo tema.
    CONSULTAS = [
        # TEMA 1: Geopolítica y guerra — cómo afectan al oro en el mundo
        # (Francia, Oriente Medio, Trump aranceles, tensiones globales)
        ('"oro" AND ("guerra" OR "aranceles" OR "Trump" OR "geopolítica" OR '
         '"Oriente Medio" OR "misil" OR "tensión" OR "repatriación")', 2),

        # TEMA 2: Bancos centrales, BRICS, reservas — tendencias macro globales
        ('"reservas de oro" OR "repatriación de oro" OR "bancos centrales" AND "oro" '
         'OR "brics" AND "oro" OR "lingote de oro" OR "banco central" AND "oro"', 2),

        # TEMA 3: Colombia local — Medellín, minería, esmeraldas, regulación
        # (lo que pasa en el patio de casa)
        ('(Colombia OR Medellín OR Bogotá OR Boyacá OR Antioquia) AND '
         '("oro" OR "esmeraldas" OR "minería" OR "muzo" OR "marmato" OR "chivor")', 2),

        # TEMA 4: Cotización y precio — solo 2, no saturar
        ('"precio del oro" OR "cotización del oro" OR "precio de la plata" '
         'OR "cotización de la plata" OR "onza de oro"', 2),

        # TEMA 5: Diamantes — crisis, laboratorio, cierre de minas
        ('"industria del diamante" OR "diamantes de laboratorio" OR '
         '"diamantes sintéticos" OR "crisis del diamante" OR "mina de diamantes"', 1),

        # TEMA 6: Plata, platino, paladio — mercado e inversión
        ('"mercado de la plata" OR "precio de la plata" OR "platino" OR "paladio" '
         'OR "metales preciosos" AND ("inversión" OR "refugio" OR "rally" OR "récord")', 2),

        # TEMA 7: Minería global — récords, grandes empresas, África, Asia
        # (Zimbabue récord, Singapur hub, top 50 mineras, Aris Mining Colombia)
        ('"producción de oro" AND ("récord" OR "record") OR '
         '"compañía minera" AND "oro" OR "Zimbabue" AND "oro" OR '
         '"Singapur" AND "oro" OR "minería aurífera" AND ("récord" OR "record")', 2),
    ]

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    }

    for query, max_por_consulta in CONSULTAS:
        if len(noticias_validas) >= 10:
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

                # FILTRO 0: solo noticias de las ultimas 36h
                try:
                    fecha_pub = parsedate_to_datetime(pub_date)
                    if fecha_pub < hace_36h:
                        continue
                except Exception:
                    pass  # si no se parsea la fecha, se incluye igual

                texto_check = (titulo + " " + desc).lower()

                # FILTRO 1: basura fuera (Vietnam, juegos, moda, deporte)
                if any(b in texto_check for b in BASURA):
                    continue
                # FILTRO 2: debe tener contexto real de metales/gemas
                if not any(c in texto_check for c in CONTEXTO_MERCADO):
                    continue
                # FILTRO 3: sin repetidos historicos entre ejecuciones
                if gestionar_historial(titulo):
                    continue
                # FILTRO 4: sin duplicados en esta tanda (misma historia, distinta fuente)
                clave = normalizar_titulo(titulo)
                if clave in titulos_vistos:
                    continue
                titulos_vistos.add(clave)

                noticias_validas.append({'title': titulo, 'url': link})
                encontrados_esta_consulta += 1
                print(f"[NOTICIAS] [{encontrados_esta_consulta}/{max_por_consulta}] {titulo[:65]}")

        except Exception as e:
            print(f"[NOTICIAS] Error en consulta: {e}")

    print(f"[NOTICIAS] Total encontradas: {len(noticias_validas)}")
    return noticias_validas


def tarea_noticias(fecha):
    print("[NOTICIAS] Iniciando...")
    arts = obtener_noticias()

    if not arts:
        enviar_telegram(
            "⚠️ <b>AGENTE CRIPGOLD — SIN NOTICIAS</b>\n"
            "No se encontraron noticias nuevas sobre metales y gemas en las ultimas 36h.\n"
            "Puede ser un dia sin novedades o un problema de conectividad."
        )
        print("[NOTICIAS] Sin resultados válidos hoy.")
        return

    folio = gestionar_folio("noticias")
    msg = (
        f"💎 <b>NOTICIAS — METALES Y GEMAS</b> 🏆\n"
        f"📅 <i>{fecha}    #{folio}</i>\n\n"
    )
    for i, art in enumerate(arts, 1):
        msg += f"<b>{i}.</b> <a href='{art['url']}'>{art['title']}</a>\n"

    msg += "\n🤖 <i>Agente CripGold — Investigación finalizada.</i>"
    enviar_telegram(msg)
    print(f"[NOTICIAS] OK — {len(arts)} noticias enviadas.")


# ============================================================
#   MAIN — Punto de entrada
# ============================================================

if __name__ == "__main__":
    fecha = datetime.datetime.now().strftime('%d/%m/%Y')
    print(f"\n{'='*50}")
    print(f"  AGENTE CRIPGOLD V2 — {fecha}")
    print(f"{'='*50}\n")

    # Aviso de inicio
    enviar_telegram(f"🤖 <b>Agente CripGold V2 — Iniciado</b>\n📅 {fecha}")

    # Ejecutar tareas
    tarea_precios(fecha)
    tarea_noticias(fecha)

    # Aviso de cierre
    enviar_telegram("✅ <b>Agente CripGold — Tareas completadas.</b>")
    print("\n[DONE] Agente finalizado correctamente.")
