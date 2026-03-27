import requests
import xml.etree.ElementTree as ET

# Test Goldprice.org
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json'
}
try:
    url = "https://data-asg.goldprice.org/dbXRates/COP"
    res = requests.get(url, headers=headers)
    data = res.json()
    oro_oz_cop = data['items'][0]['xauPrice']
    oro_g_cop = oro_oz_cop / 31.1034768
    print(f"GoldPrice.org: {oro_oz_cop} COP/oz -> {oro_g_cop} COP/g")
except Exception as e:
    print(f"GoldPrice Error: {e}")

# Test Google News
try:
    url = "https://news.google.com/rss/search?q=(oro OR esmeraldas OR diamantes OR plata) AND (inversión OR mercado OR precio) -futbol -deportes&hl=es-419&gl=CO&ceid=CO:es-419"
    res = requests.get(url)
    root = ET.fromstring(res.text)
    items = root.findall('.//item')
    print(f"Google News Found: {len(items)}")
    for item in items[:5]:
        tit = item.find('title').text
        print("- " + tit)
except Exception as e:
    print(f"Google News Error: {e}")
