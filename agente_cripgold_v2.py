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
    """Elimina fechas y días del título para detectar artículos repetidos con distinta fecha."""
    import re
    t = titulo.lower()
    t = re.sub(r'\d{1,2} de \w+ de \d{4}', '', t)
    t = re.sub(r'(lunes|martes|miércoles|jueves|viernes|sábado|domingo)', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:60]

def obtener_noticias():
    """
    Consulta NewsAPI solo en español.
    Lógica: La query de NewsAPI ya filtra por tema. Luego el filtro local
    elimina basura (premios, deportes, política) y exige que aparezca
    al menos una palabra clave de metales/gemas en el texto.
    """
    ahora = datetime.datetime.utcnow()
    # 96h para maximizar volumen de noticias disponibles
    hace_96h = (ahora - datetime.timedelta(hours=96)).strftime('%Y-%m-%dT%H:%M:%S')

    # ── FRASES COMPUESTAS obligatorias ─────────────────────────────────────
    # Estas frases SOLO aparecen en noticias reales del mercado de metales.
    # "precio del oro" jamás aparece en un artículo de Mar del Plata o Free Fire.
    CONTEXTO_MERCADO = [
        "precio del oro", "cotización del oro", "onza de oro",
        "mercado del oro", "reservas de oro", "lingote de oro",
        "minería de oro", "minería aurífera", "oro físico",
        "inversión en oro", "demanda de oro", "compra de oro",
        "precio de la plata", "cotización de la plata", "onza de plata",
        "mercado de la plata", "lingote de plata", "plata física",
        "inversión en plata", "demanda de plata",
        "precio del platino", "precio del paladio", "paladio",
        "metales preciosos", "metal precioso",
        "esmeralda", "esmeraldas",
        "diamante industrial", "mercado de diamantes", "industria del diamante",
        "mina de diamantes", "producción de diamantes",
        "piedra preciosa", "piedras preciosas", "gema", "gemas",
        "muzo", "marmato", "chivor",
        "banco central compra oro", "brics oro", "reservas en oro",
        "fondo de oro", "etf de oro", "futuros del oro",
        # ── Frases adicionales verificadas en búsquedas reales ──
        "bancos centrales compran oro", "bancos centrales y el oro",
        "reservas de oro de los bancos", "brics y el oro",
        "refugio de valor en oro", "oro como refugio",
        "centenario de oro", "centenarios de oro",
        "oro y plata como inversión", "oro y plata suben",
        "metales del grupo platínico",
        "diamantes sintéticos", "diamantes de laboratorio",
        "esmeraldas colombianas", "mineros de esmeraldas",
        "récord del oro", "máximo histórico del oro",
        "precio spot del oro", "mercado de futuros del oro",
    ]

    # ── ELIMINACIÓN INMEDIATA ────────────────────────────────────────────
    BASURA = [
        # Videojuegos (Free Fire, LoL, etc. usan oro/plata/diamante como rangos)
        "free fire", "freefire", "códigos de hoy", "recompensas gratis",
        "league of legends", "clash of clans", "clash royale", "fortnite",
        "valorant", "pubg", "mobile legends", "honor of kings",
        "battle royale", "videojuego", "gaming", "gamer", "gameplay",
        "rango de oro", "rango de plata", "rango de diamante",
        "temporada de juego", "pase de batalla", "loot",
        # Moda / farándula / joyería de celebridades
        "broche de diamante", "collar de diamante", "pulsera de oro",
        "anillo de oro", "joyería de moda", "bisutería",
        "lució", "llevó puesto", "vistió con", "portó un",
        "reina camilla", "kate middleton", "meghan markle",
        "alfombra roja", "look de", "outfit", "tendencia de moda",
        "diseño de joyas", "colección de joyas", "joya real",
        "novia real", "boda real",
        # Ciudades y ríos con "plata" u "oro"
        "mar del plata", "río de la plata", "la plata",
        # Crímenes y accidentes
        "estafa", "robo", "hurto", "accidente", "murió", "falleció",
        "chocó", "detuvo", "arrestó", "capturó", "secuestro",
        "homicidio", "asesinó", "mató", "herido", "víctima",
        # Deportes
        "fútbol", "futbol", "balón de oro", "bola de oro", "gol de oro",
        "medalla de oro", "copa de oro", "nba", "nfl", "champions",
        "premier league", "liga endesa", "embajadora", "laureus",
        "atletismo", "ciclismo", "tenis", "boxeo",
        # Entretenimiento
        "premio platino", "premios platino", "spirit awards",
        "golden globe", "bafta", "emmy", "grammy", "bts", "kpop",
        "concierto", "gira musical", "festival de cine",
        "trayectoria artística", "actor", "actriz", "estreno de", "película",
        # Política sin metales
        "juez federal", "espía rusa", "antisemita", "zelenski",
        "congreso", "senado", "elecciones", "campaña electoral",
        # Economía general
        "plazo fijo", "tasa de interés", "cepo al dólar", "dólar blue",
        "granos", "soja", "trigo", "maíz", "cosecha", "ganadería",
        "monedas dejarán de circular", "retiro de monedas",
        "billete", "papel moneda", "tarjeta de crédito",
        # Tecnología / otros
        "samsung", "xiaomi", "iphone", "apple", "receta", "cocina",
        "zara", "ropa", "celular", "smartphone", "biblioteca",
        "movistar plus", "el corte inglés",
        # Metáforas
        "corazón de oro", "edad de oro", "regla de oro",
        "color dorado", "color oro", "boda de plata", "disco de oro",
    ]

    noticias_validas = []
    titulos_vistos  = set()

    # CONSULTA 1 — Frases exactas del mercado (no hay ambigüedad posible)
    q_mercado = (
        '"precio del oro" OR "cotización del oro" OR "onza de oro" OR '
        '"precio de la plata" OR "cotización de la plata" OR '
        '"reservas de oro" OR "lingote de oro" OR "mercado del oro" OR '
        '"minería de oro" OR "minería aurífera" OR "metales preciosos" OR '
        '"precio del platino" OR "precio del paladio" OR '
        '"mercado de diamantes" OR "industria del diamante" OR '
        'esmeraldas OR "piedras preciosas" OR muzo OR marmato OR chivor'
    )

    # CONSULTA 2 — Colombia y LATAM con frases de mercado
    q_latam = (
        '(Colombia OR Bogotá OR Medellín OR Venezuela OR Perú OR Ecuador OR '
        'México OR Chile OR Brasil OR "Banco de la República" OR "América Latina") AND '
        '("precio del oro" OR "precio de la plata" OR esmeraldas OR '
        '"minería de oro" OR "minería aurífera" OR "metales preciosos" OR '
        '"piedras preciosas" OR muzo OR marmato OR chivor OR '
        '"lingote de oro" OR "onza de oro" OR "reservas de oro" OR '
        '"mercado de diamantes")'
    )

    # CONSULTA 3 — Medios financieros especializados LATAM
    # Dominios verificados: fuentes donde SÍ aparecen noticias del sector hoy
    DOMINIOS = (
        "portafolio.co,larepublica.co,dinero.com,semana.com,"
        "elcolombiano.com,infobae.com,expansion.mx,"
        "eleconomista.com.mx,df.cl,americaeconomia.com,"
        "mineriaenlinea.com,bloomberglinea.com,sercolombiano.com,"
        "dipromin.com,preciooro.com,kitco.com,investing.com"
    )
    q_financiero = (
        '"precio del oro" OR "precio de la plata" OR esmeraldas OR '
        '"metales preciosos" OR "piedras preciosas" OR '
        '"mercado de diamantes" OR "minería de oro" OR muzo OR marmato'
    )

    # CONSULTA 4 — Macrotendencias: bancos centrales, BRICS, refugio, récords
    q_macro = (
        '"bancos centrales" AND ("oro" OR "plata" OR "metales preciosos") OR '
        '"brics" AND "oro" OR '
        '"refugio de valor" AND ("oro" OR "plata") OR '
        '"récord del oro" OR "record del oro" OR "máximo histórico" AND "oro" OR '
        '"diamantes sintéticos" OR "diamantes de laboratorio" OR '
        '"esmeraldas colombianas" OR "mineros artesanales" AND "esmeraldas"'
    )

    consultas = [
        (q_mercado,    None),
        (q_latam,      None),
        (q_financiero, DOMINIOS),
        (q_macro,      None),
    ]

    for q, dominios in consultas:
        if len(noticias_validas) >= 10:
            break
        params = {
            'q': q,
            'language': 'es',
            'sortBy': 'publishedAt',
            'from': hace_96h,
            'apiKey': NEWS_KEY,
            'pageSize': 100
        }
        if dominios:
            params['domains'] = dominios
        try:
            res  = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
            data = res.json()
            if data.get('status') != 'ok':
                print(f"[NOTICIAS] NewsAPI: {data.get('message','')}")
                continue
            for art in data.get('articles', []):
                if len(noticias_validas) >= 10:
                    break
                titulo = (art.get('title') or "").strip()
                desc   = (art.get('description') or "").strip()
                url    = art.get('url', "")
                if not titulo or titulo == "[Removed]":
                    continue
                texto_check = (titulo + " " + desc).lower()

                # FILTRO 1: basura fuera
                if any(b in texto_check for b in BASURA):
                    continue
                # FILTRO 2: debe tener contexto real de mercado de metales/gemas
                if not any(c in texto_check for c in CONTEXTO_MERCADO):
                    continue
                # FILTRO 3: sin repetidos históricos
                if gestionar_historial(titulo):
                    continue
                # FILTRO 4: sin repetidos en esta tanda
                # Normaliza fecha del título para evitar "mismo artículo, día diferente"
                clave = normalizar_titulo(titulo)
                if clave in titulos_vistos:
                    continue
                titulos_vistos.add(clave)

                noticias_validas.append({'title': titulo, 'url': url})

        except Exception as e:
            print(f"[NOTICIAS] Error: {e}")

    return noticias_validas


def tarea_noticias(fecha):
    print("[NOTICIAS] Iniciando...")
    arts = obtener_noticias()

    if not arts:
        enviar_telegram(
            "⚠️ <b>AGENTE CRIPGOLD — SIN NOTICIAS</b>\n"
            "No se encontraron noticias nuevas sobre metales y gemas en las últimas 48h.\n"
            "Puede ser un día sin novedades o un problema con NewsAPI."
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
