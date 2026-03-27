import requests
headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/XAU=X?interval=1d&range=1d", headers=headers)
oro_usd = res.json()['chart']['result'][0]['meta']['regularMarketPrice']
res_cop = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/COP=X?interval=1d&range=1d", headers=headers)
usd_cop = res_cop.json()['chart']['result'][0]['meta']['regularMarketPrice']
base_pura = (float(oro_usd) / 31.1034768) * float(usd_cop)
print(f"XAU=X: {oro_usd}, COP=X: {usd_cop}, Base Pura: {base_pura}")
