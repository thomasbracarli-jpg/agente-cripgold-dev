import requests
headers = {'User-Agent': 'Mozilla/5.0'}
res = requests.get("https://query2.finance.yahoo.com/v1/finance/search?q=oro", headers=headers)
data = res.json()
for n in data.get('news', [])[:5]:
    print(n['title'])
