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

    # FUENTE 2: Yahoo Finance como respaldo
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

    # TRM: USD a COP
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
            "No se pudo obtener el precio del oro.\n"
            "Verifica manualmente: <a href='https://goldprice.org'>goldprice.org</a>"
        )
        print("[PRECIOS] ERROR: no se obtuvo precio.")
        return

    folio = gestionar_folio("precios")

    encabezado = (
        f"📊 <b>Mercado hoy:</b>\n"
        f"🥇 Oro: <b>${oro_usd:,.2f} USD/oz</b>\n"
        f"💵 TRM: <b>${usd_cop:,.2f} COP/USD</b>\n"
        f"⚖️ Gramo 24K: <b>${gramo_cop:,.0f} COP</b>"
    )
    enviar_telegram(encabezado)

    msg_83 = construir_mensaje_precios(gramo_cop, 0.83, folio, fecha)
    enviar_telegram(msg_83)

    msg_84 = construir_mensaje_precios(gramo_cop, 0.84, folio, fecha)
    enviar_telegram(msg_84)

    print(f"[PRECIOS] OK — gramo 24K: ${gramo_cop:,.0f} COP")


# ============================================================
#   TAREA 2 — NOTICIAS MERCADO DE METALES Y GEMAS
# ============================================================

def obtener_noticias():
    ahora = datetime.datetime.utcnow()
    hace_48h = (ahora - datetime.timedelta(hours=48)).strftime('%Y-%m-%dT%H:%M:%S')

    METALES_DIRECTOS = [
        "precio del oro", "precio de la plata", "precio del platino",
        "oro físico", "plata física", "lingote de oro", "lingote de plata",
        "onza de oro", "onza de plata",
        "reservas de oro", "minería de oro", "explotación de oro",
        "mercado del oro", "cotización del oro", "cotización de la plata",
        "esmeralda", "esmeraldas de muzo", "esmeraldas colombianas",
        "diamante", "mercado de diamantes", "piedra preciosa", "gema",
        "platino como metal", "precio del platino", "paladio",
        "banco central compra oro", "brics oro",
        "fiebre del oro", "muzo", "marmato", "chivor",
        "metal precioso", "metales preciosos"
    ]

    PALABRAS_BASURA = [
        # Deportes
        "fútbol", "futbol", "soccer", "balón de oro", "bola de oro",
        "gol de oro", "medalla de oro", "copa de oro", "nba", "nfl",
        "champions", "premier league", "liga endesa", "new balance",
        # Premios de entretenimiento — "platino", "plata", "oro" en contexto artístico
        "premio platino", "premios platino", "pelean el platino",
        "spirit awards", "golden globe", "bafta", "emmy", "grammy",
        "festival de cine", "trayectoria artística", "actor", "actriz",
        "serie", "temporada", "película", "pelicula", "estreno", "cine",
        # Política sin relación a metales
        "zelenski", "congreso", "senado", "elecciones", "partido político",
        "campaña electoral", "reforma tributaria", "reforma pensional",
        # Economía general sin metales
        "plazo fijo", "tasa de interés", "cepo al dólar", "dólar blue",
        "flexibilizaciones del cepo", "acopio de granos", "granos",
        "soja", "trigo", "maíz", "cosecha", "agro", "agricultura",
        "ganadería", "monedas dejarán de circular", "retiro de monedas",
        "de curso legal", "billete", "papel moneda",
        # Tecnología / moda
        "samsung", "xiaomi", "iphone", "apple", "android",
        "receta", "cocina", "chef", "restaurante", "zara", "moda", "ropa",
        "celular", "teléfono", "smartphone", "laptop", "tablet", "videojuego",
        # Metáforas
        "corazón de oro", "golden gate", "edad de oro", "regla de oro",
        "hora dorada", "color dorado", "color oro", "acabado dorado",
        "aniversario de oro", "boda de oro", "boda de plata",
        "disco de oro", "disco de plata", "récord de oro",
        "movistar plus", "el corte inglés"
    ]

    noticias_validas = []
    titulos_vistos = set()

    # CONSULTA 1 — Noticias internacionales de metales y gemas en español
    q_general = (
        '("precio del oro" OR "precio de la plata" OR "esmeraldas" OR '
        '"lingotes de oro" OR "onza de oro" OR "minería de oro" OR '
        '"reservas de oro" OR "cotización del oro" OR "mercado del oro" OR '
        '"banco central compra oro" OR "BRICS oro" OR "metal precioso" OR '
        '"paladio" OR "diamantes" OR "piedras preciosas")'
    )

    # CONSULTA 2 — Noticias locales Colombia y LATAM
    q_latam = (
        '(Colombia OR "América Latina" OR Latinoamérica OR Venezuela OR Perú OR '
        'Ecuador OR México OR Chile OR Brasil OR "Banco de la República") AND '
        '("oro" OR "plata" OR "esmeraldas" OR "minería" OR "metales preciosos" OR '
        '"muzo" OR "marmato" OR "chivor" OR "diamantes" OR "piedras preciosas")'
    )

    for q in [q_general, q_latam]:
        if len(noticias_validas) >= 10:
            break
        params = {
            'q': q,
            'language': 'es',
            'sortBy': 'publishedAt',
            'from': hace_48h,
            'apiKey': NEWS_KEY,
            'pageSize': 100
        }
        try:
            res = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
            data = res.json()
            if data.get('status') != 'ok':
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

                # FILTRO 1: descarte por basura
                if any(b in texto_check for b in PALABRAS_BASURA):
                    continue

                # FILTRO 2 (OBLIGATORIO): debe mencionar metal/gema directamente
                if not any(m in texto_check for m in METALES_DIRECTOS):
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
        enviar_telegram(
            "⚠️ <b>AGENTE CRIPGOLD — SIN NOTICIAS</b>\n"
            "No se encontraron noticias nuevas sobre metales y gemas en las últimas 48h."
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

    enviar_telegram(f"🤖 <b>Agente CripGold V2 — Iniciado</b>\n📅 {fecha}")

    tarea_precios(fecha)
    tarea_noticias(fecha)

    enviar_telegram("✅ <b>Agente CripGold — Tareas completadas.</b>")
    print("\n[DONE] Agente finalizado correctamente.")
