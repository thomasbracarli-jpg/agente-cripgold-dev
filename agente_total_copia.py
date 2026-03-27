from flask import Flask
import requests
import datetime
import time
import os

app = Flask(__name__)

# --- CONFIGURACIÓN ---
TOKEN = '8678579635:AAFbm5FMzbuDKYCnL_ttmoI0Zq5_ytRrYYM'
DESTINATARIOS = ['8526092375', '5503549435', '6915327599'] 
NEWS_KEY = '7b7920c95da342c7bf56602283cfb5a7'

# --- MANEJO DE REGISTRO (FOLIO) ---
def gestionar_folio(tipo):
    nombre_archivo = nombre_archivo = os.path.join(os.path.dirname(__file__), f"contador_{tipo}.txt")

    # Ajuste de ruta para PythonAnywhere
    if not os.path.exists(nombre_archivo):
        with open(nombre_archivo, "w") as f: f.write("1")
        return 1
    with open(nombre_archivo, "r") as f:
        try: actual = int(f.read().strip())
        except: actual = 0
    nuevo = actual + 1
    with open(nombre_archivo, "w") as f: f.write(str(nuevo))
    return nuevo

# --- FUNCIONES DE APOYO ---
def enviar_telegram(texto):
    for chat_id in DESTINATARIOS:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': texto, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
        try: requests.post(url, data=payload)
        except: pass

def obtener_precios():
    headers = {'User-Agent': 'Mozilla/5.0'}
    # Multiples fuentes de respaldo (XAUUSD=X, XAUUSD=P, GC=F, XAU=X)
    tickers_oro = ["XAUUSD=X", "XAUUSD=P", "GC=F", "XAU=X"]
    oro_usd = None
    for t in tickers_oro:
        try:
            res = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1d&range=5d", headers=headers, timeout=10)
            oro_usd = res.json()['chart']['result'][0]['meta']['regularMarketPrice']
            if oro_usd: break
        except: continue
    
    try:
        res_cop = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/COP=X?interval=1d&range=5d", headers=headers, timeout=10)
        usd_cop = res_cop.json()['chart']['result'][0]['meta']['regularMarketPrice']
        if oro_usd and usd_cop:
            # Calculo financiero puro y exacto (Spot del Mercado Mundial)
            return (float(oro_usd) / 31.1034768) * float(usd_cop)
    except: pass
    return None

def obtener_noticias():
    noticias = []
    titulos_fijos = set()
    
    # LA LISTA BLANCA (Solo élite financiera y oficial, nada de blogs o foros)
    fuentes_elite = "bloomberglinea.com,es.finance.yahoo.com,finance.yahoo.com,reuters.com,forbes.com,forbes.co,eleconomista.es,expansion.com,portafolio.co,larepublica.co,valoraanalitik.com,cnbc.com,wsj.com,ft.com,cnn.com"
    
    # LA LISTA NEGRA (Muro final contra la basura publicitaria o deportiva)
    malo = ["fútbol", "deporte", "oscar", "estreno", "liga", "copa", "partido", "gol", "bitcoin", "cripto", "xokas", "influencer", "tiktok", "cine", "pelicula", "promoción", "publicidad", "oferta", "serie", "televisión"]
    
    # LA LISTA BLANCA (Requisito absoluto local en el título)
    bueno = ["oro", "plata", "esmeralda", "diamante", "joya", "minería", "precio", "onza", "quilate", "inversión", "mercado", "joyería", "metal", "mina", "hallazgo", "banco central", "geopolítica"]
    
    # LAS ECUACIONES DE BÚSQUEDA PRECISA (Basadas en tus directrices)
    # Grupo 1: Geopolítica, Bancos Centrales y Mercados
    q_mercados = '+(oro OR plata) +(geopolítica OR guerra OR "banco central" OR "bancos centrales" OR mercado OR reserva)'
    # Grupo 2: Industria Joyera, Famosos, Costosas y Piedras
    q_joyas = '+(joyería OR joyas) +(diamante OR esmeralda OR platino OR rubí OR rubíes OR zafiro OR zafiros OR paladio OR famosos OR costosas OR lujo)'
    # Grupo 3: Hallazgos e Industria Minera de Metales Preciosos
    q_minas = '+(mina OR hallazgo OR minería OR comodities) +(oro OR plata OR metales OR diamantes)'
    
    # Jerarquía de importancia para llegar a las 10 noticias (4, 3, 3)
    temas = [
        (q_mercados, 4),
        (q_joyas, 3),
        (q_minas, 3)
    ]
    
    for query, cant in temas:
        params = {
            'q': query, 
            'language': 'es', 
            'sortBy': 'relevancy', # Priorizamos relevancia en las fuentes élite, no solo frescura
            'domains': fuentes_elite, # EL BLINDAJE DE FUENTES
            'apiKey': NEWS_KEY, 
            'pageSize': 20
        }
        try:
            res = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10).json()
            if res.get('status') == 'ok':
                arts = res.get('articles', [])
                agregados = 0
                for art in arts:
                    if agregados >= cant: break
                    titulo = art.get('title', '').strip().lower()
                    
                    if titulo not in titulos_fijos and not any(m in titulo for m in malo):
                        if any(b in titulo for b in bueno):
                            noticias.append(art)
                            titulos_fijos.add(titulo)
                            agregados += 1
        except: pass
    
    # Relleno de seguridad extremo en caso de que alguna ecuación no arroje suficientes noticias de ayer a hoy.
    if len(noticias) < 10:
        params_emergencia = {
            'q': 'oro OR metales preciosos OR joyería', 
            'language': 'es', 'sortBy': 'publishedAt', 
            'domains': fuentes_elite,
            'apiKey': NEWS_KEY, 'pageSize': 20
        }
        try:
            res = requests.get("https://newsapi.org/v2/everything", params=params_emergencia, timeout=10).json()
            if res.get('status') == 'ok':
                for art in res.get('articles', []):
                    if len(noticias) >= 10: break
                    titulo = art.get('title', '').strip().lower()
                    if titulo not in titulos_fijos and not any(m in titulo for m in malo):
                        if any(b in titulo for b in bueno):
                            noticias.append(art)
                            titulos_fijos.add(titulo)
        except: pass
        
    return noticias[:10]

# === RUTA PRINCIPAL (DISPARADOR) ===
@app.route('/')
@app.route('/disparar')
def disparar_agente():
    fecha = datetime.datetime.now().strftime('%d/%m/%Y')
    
    # 1. Precios
    oro_g = obtener_precios()
    if oro_g:
        folio_p = gestionar_folio("precios")
        def f(v): return f"{int(v):,.0f}".replace(",", ".")
        def fr(v): return f"{int(round(v/1000)*1000):,.0f}".replace(",", ".")
        base = oro_g * 0.83
        msg_p = f"💰 <b>PRECIOS DE COMPRA CRIPGOLD</b> 💰\n📅 <i>{fecha}    #{folio_p}</i>\n"
        msg_p += "➖➖➖➖➖➖➖➖➖➖\n\n<b>ORO</b>\n(precios exactos)\n"
        msg_p += f"BASE {f(base)}\n\n18K ITALY - {f(base*0.74)}\n17K NACIONAL - {f(base*0.71)}\n16K - {f(base*0.69)}\n15K - {f(base*0.62)}\n14K - {f(base*0.575)}\n10K - {f(base*0.40)}\n\n"
        msg_p += f"<b>ORO</b>\n(precios redondeados)\nBASE {fr(base)}\n\n18K ITALY - {fr(base*0.74)}\n17K NACIONAL - {fr(base*0.71)}\n16K - {fr(base*0.69)}\n15K - {fr(base*0.62)}\n14K - {fr(base*0.575)}\n10K - {fr(base*0.40)}\n"
        msg_p += "➖➖➖➖➖➖➖➖➖➖\n🤖 <i>Agente de Precios CripGold</i>"
        enviar_telegram(msg_p)
    
    # 2. Noticias
    arts = obtener_noticias()
    if arts:
        folio_n = gestionar_folio("noticias")
        msg_n = f"💎 <b>NOTICIAS NACIONALES E INTERNACIONALES: Inversión</b> 🏆\n📅 <i>{fecha}    #{folio_n}</i>\n\n"
        for i, art in enumerate(arts, 1):
            msg_n += f"<b>{i}.</b> <a href='{art['url']}'>{art['title']}</a>\n"
        msg_n += "\n🤖 <i>Agente Autónomo de Inversiones</i>"
        enviar_telegram(msg_n)
        
    return f"Felicidades: Reporte #{fecha} enviado a Telegram."

if __name__ == "__main__":
    app.run()
