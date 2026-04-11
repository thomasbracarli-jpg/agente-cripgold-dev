import requests
import datetime
import os

TOKEN        = os.environ.get("TELEGRAM_TOKEN", "8678579635:AAFbm5FMzbuDKYCnL_ttmoI0Zq5_ytRrYYM")
DESTINATARIOS = os.environ.get("TELEGRAM_CHATS", "8526092375,5503549435,6915327599").split(",")
NEWS_KEY     = os.environ.get("NEWS_API_KEY", "600c50b8de384fa88ba678ab4724d738")

def enviar_telegram(texto):
    for chat_id in DESTINATARIOS:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': texto, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
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

def obtener_precio_oro_cop():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    oro_usd = None
    try:
        res_gp = requests.get("https://data-asg.goldprice.org/dbXRates/USD", headers=headers, timeout=12)
        if res_gp.status_code == 200:
            precio_gp = res_gp.json()['items'][0]['xauPrice']
            if precio_gp and float(precio_gp) > 100:
                oro_usd = float(precio_gp)
                print(f"[PRECIOS] goldprice.org: ${oro_usd}")
    except Exception as e:
        print(f"[PRECIOS] goldprice.org falló: {e}")
    if not oro_usd:
        for ticker in ["XAUUSD=X", "GC=F"]:
            try:
                res_yf = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d", headers=headers, timeout=12)
                if res_yf.status_code == 200:
                    p = res_yf.json()['chart']['result'][0]['meta']['regularMarketPrice']
                    if p and float(p) > 100:
                        oro_usd = float(p)
                        break
            except:
                continue
    usd_cop = None
    try:
        res_cop = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/COP=X?interval=1d&range=5d", headers=headers, timeout=12)
        if res_cop.status_code == 200:
            usd_cop = float(res_cop.json()['chart']['result'][0]['meta']['regularMarketPrice'])
    except:
        pass
    if oro_usd and usd_cop:
        return oro_usd, usd_cop, (oro_usd / 31.1034768) * usd_cop
    return None, None, None

def construir_mensaje_precios(base_gramo, porcentaje, folio, fecha):
    base = base_gramo * porcentaje
    etiqueta = f"{int(porcentaje * 100)}%"
    def f(v): return f"{int(v):,.0f}".replace(",", ".")
    def fr(v): return f"{int(round(v / 1000) * 1000):,.0f}".replace(",", ".")
    return (
        f"💰 <b>PRECIOS DE COMPRA CRIPGOLD</b> 💰\n"
        f"📅 <i>{fecha}    #{folio} — Base {etiqueta}</i>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n\n"
        f"<b>ORO</b>  <i>(precios exactos)</i>\n"
        f"BASE {f(base)}\n\n"
        f"18K ITALY    — {f(base * 0.74)}\n17K NACIONAL — {f(base * 0.71)}\n"
        f"16K          — {f(base * 0.69)}\n15K          — {f(base * 0.62)}\n"
        f"14K          — {f(base * 0.575)}\n10K          — {f(base * 0.40)}\n\n"
        f"<b>ORO</b>  <i>(precios redondeados)</i>\n"
        f"BASE {fr(base)}\n\n"
        f"18K ITALY    — {fr(base * 0.74)}\n17K NACIONAL — {fr(base * 0.71)}\n"
        f"16K          — {fr(base * 0.69)}\n15K          — {fr(base * 0.62)}\n"
        f"14K          — {fr(base * 0.575)}\n10K          — {fr(base * 0.40)}\n"
        f"➖➖➖➖➖➖➖➖➖➖"
    )

def tarea_precios(fecha):
    print("[PRECIOS] Iniciando...")
    oro_usd, usd_cop, gramo_cop = obtener_precio_oro_cop()
    if not gramo_cop:
        enviar_telegram("⚠️ <b>AGENTE CRIPGOLD — ERROR EN PRECIOS</b>\nVerifica: <a href='https://goldprice.org'>goldprice.org</a>")
        return
    folio = gestionar_folio("precios")
    enviar_telegram(f"📊 <b>Mercado hoy:</b>\n🥇 Oro: <b>${oro_usd:,.2f} USD/oz</b>\n💵 TRM: <b>${usd_cop:,.2f} COP/USD</b>\n⚖️ Gramo 24K: <b>${gramo_cop:,.0f} COP</b>")
    enviar_telegram(construir_mensaje_precios(gramo_cop, 0.83, folio, fecha))
    enviar_telegram(construir_mensaje_precios(gramo_cop, 0.84, folio, fecha))
    print(f"[PRECIOS] OK — ${gramo_cop:,.0f} COP/g")

def obtener_noticias():
    ahora = datetime.datetime.utcnow()
    hace_72h = (ahora - datetime.timedelta(hours=72)).strftime('%Y-%m-%dT%H:%M:%S')

    # ── FRASES COMPUESTAS: solo aparecen en noticias genuinas del sector ──
    # "precio del oro" nunca aparece en una nota de Mar del Plata.
    CONTEXTO_MERCADO = [
        # Oro como metal / mercado
        "precio del oro", "cotización del oro", "onza de oro",
        "mercado del oro", "reservas de oro", "lingote de oro",
        "minería de oro", "minería aurífera", "oro físico",
        "inversión en oro", "demanda de oro", "oferta de oro",
        # Plata como metal / mercado
        "precio de la plata", "cotización de la plata", "onza de plata",
        "mercado de la plata", "lingote de plata", "plata física",
        "inversión en plata", "demanda de plata",
        # Gemas — palabras menos ambiguas, no necesitan frase
        "esmeralda", "esmeraldas", "diamante", "diamantes",
        "piedra preciosa", "piedras preciosas", "gema", "gemas",
        # Otros metales preciosos
        "precio del platino", "precio del paladio", "paladio",
        "metales preciosos",
        # Lugares específicos de minería colombiana
        "muzo", "marmato", "chivor",
    ]

    # ── ELIMINACIÓN INMEDIATA ─────────────────────────────────────────────
    BASURA = [
        # Ciudades y ríos que contienen "plata" u "oro"
        "mar del plata", "río de la plata", "la plata", "villa del parque",
        "puerto madryn", "bahía blanca",
        # Crímenes, accidentes, sucesos (mencionan "oro" de paso)
        "estafa", "robo", "hurto", "accidente", "murió", "falleció",
        "chocó", "detuvo", "arrestó", "capturó", "secuestro",
        "homicidio", "asesinó", "mató", "herido",
        # Deportes
        "fútbol", "futbol", "balón de oro", "bola de oro", "gol de oro",
        "medalla de oro", "copa de oro", "nba", "nfl", "champions",
        "premier league", "liga endesa", "embajadora", "laureus",
        # Entretenimiento / espectáculos
        "premio platino", "premios platino", "spirit awards",
        "golden globe", "bafta", "emmy", "grammy", "bts", "kpop",
        "concierto", "gira", "festival de cine", "trayectoria artística",
        "actor", "actriz", "serie televisiva", "temporada", "estreno",
        # Política sin metales
        "juez federal", "espía", "antisemita", "zelenski",
        "congreso", "senado", "elecciones", "campaña electoral",
        # Economía general sin metales
        "plazo fijo", "tasa de interés", "cepo al dólar", "dólar blue",
        "granos", "soja", "trigo", "maíz", "cosecha", "ganadería",
        "monedas dejarán de circular", "retiro de monedas",
        "billete", "papel moneda", "tarjeta de crédito",
        # Tecnología / moda / otros
        "samsung", "xiaomi", "iphone", "apple", "receta", "cocina",
        "zara", "moda", "ropa", "celular", "smartphone", "videojuego",
        # Metáforas comunes
        "corazón de oro", "edad de oro", "regla de oro",
        "color dorado", "color oro", "boda de plata", "disco de oro",
        "movistar plus", "el corte inglés", "biblioteca"
    ]

    noticias_validas = []
    titulos_vistos = set()

    # CONSULTA 1 — Frases exactas del mercado de metales en español
    q_mercado = (
        '"precio del oro" OR "cotización del oro" OR "onza de oro" OR '
        '"precio de la plata" OR "cotización de la plata" OR '
        '"reservas de oro" OR "lingote de oro" OR "mercado del oro" OR '
        '"minería de oro" OR "minería aurífera" OR "metales preciosos" OR '
        '"precio del platino" OR "precio del paladio" OR '
        'esmeraldas OR diamantes OR "piedras preciosas" OR muzo OR marmato'
    )

    # CONSULTA 2 — Colombia y LATAM con frases de mercado
    q_latam = (
        '(Colombia OR Bogotá OR Medellín OR Venezuela OR Perú OR Ecuador OR '
        'México OR Chile OR Brasil OR "Banco de la República") AND '
        '("precio del oro" OR "precio de la plata" OR esmeraldas OR diamantes OR '
        '"minería de oro" OR "minería aurífera" OR "metales preciosos" OR '
        '"piedras preciosas" OR muzo OR marmato OR chivor OR lingote OR '
        '"onza de oro" OR "reservas de oro")'
    )

    # FUENTES FINANCIERAS ESPECIALIZADAS en español (LATAM + España)
    DOMINIOS_FINANCIEROS = (
        "portafolio.co,larepublica.co,dinero.com,semana.com,"
        "elcolombiano.com,eltiempo.com,caracol.com.co,"
        "infobae.com,expansion.mx,eleconomista.com.mx,"
        "elfinanciero.com.mx,df.cl,americaeconomia.com,"
        "mining.com,kitco.com,mineria-pa.com"
    )

    consultas = [
        # (query, usar_dominios_financieros)
        (q_mercado, False),         # búsqueda amplia en todo español
        (q_latam,   False),         # Colombia/LATAM sin restricción de dominio
        (q_mercado, True),          # misma query pero solo en medios financieros
    ]

    for q, usar_dominios in consultas:
        if len(noticias_validas) >= 10:
            break
        params = {
            'q': q,
            'language': 'es',
            'sortBy': 'publishedAt',
            'from': hace_72h,
            'apiKey': NEWS_KEY,
            'pageSize': 100
        }
        if usar_dominios:
            params['domains'] = DOMINIOS_FINANCIEROS

        try:
            res = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
            data = res.json()
            if data.get('status') != 'ok':
                print(f"[NOTICIAS] NewsAPI error: {data.get('message','')}")
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
                # FILTRO 1: eliminar basura
                if any(b in texto_check for b in BASURA):
                    continue
                # FILTRO 2: debe tener contexto real de mercado de metales/gemas
                if not any(c in texto_check for c in CONTEXTO_MERCADO):
                    continue
                # FILTRO 3: sin repetidos históricos
                if gestionar_historial(titulo):
                    continue
                # FILTRO 4: sin repetidos en esta tanda
                clave = titulo[:50].lower()
                if clave in titulos_vistos:
                    continue
                titulos_vistos.add(clave)
                noticias_validas.append({'title': titulo, 'url': url})
        except Exception as e:
            print(f"[NOTICIAS] Error en consulta: {e}")

    return noticias_validas

def tarea_noticias(fecha):
    print("[NOTICIAS] Iniciando...")
    arts = obtener_noticias()
    if not arts:
        enviar_telegram("⚠️ <b>AGENTE CRIPGOLD — SIN NOTICIAS</b>\nNo se encontraron noticias nuevas sobre metales y gemas.")
        return
    folio = gestionar_folio("noticias")
    msg = f"💎 <b>NOTICIAS — METALES Y GEMAS</b> 🏆\n📅 <i>{fecha}    #{folio}</i>\n\n"
    for i, art in enumerate(arts, 1):
        msg += f"<b>{i}.</b> <a href='{art['url']}'>{art['title']}</a>\n"
    msg += "\n🤖 <i>Agente CripGold — Investigación finalizada.</i>"
    enviar_telegram(msg)
    print(f"[NOTICIAS] OK — {len(arts)} noticias.")

if __name__ == "__main__":
    fecha = datetime.datetime.now().strftime('%d/%m/%Y')
    print(f"\n{'='*50}\n  AGENTE CRIPGOLD V2 — {fecha}\n{'='*50}\n")
    enviar_telegram(f"🤖 <b>Agente CripGold V2 — Iniciado</b>\n📅 {fecha}")
    tarea_precios(fecha)
    tarea_noticias(fecha)
    enviar_telegram("✅ <b>Agente CripGold — Tareas completadas.</b>")
    print("\n[DONE] Agente finalizado.")
