import requests

NEWS_KEY = '7b7920c95da342c7bf56602283cfb5a7'

queries = [
    "oro mercado OR inversión OR joyas OR precio",
    "plata mercado OR inversión OR precio",
    "esmeraldas OR diamantes mercado OR inversión OR preciosa"
]

bloqueo = " -fútbol -soccer -deportes -cine -pelicula -liga -copa"
noticias = []

for q in queries:
    params = {
        'q': q + bloqueo,
        'language': 'es',
        'sortBy': 'publishedAt',
        'apiKey': NEWS_KEY,
        'pageSize': 20
    }
    res = requests.get("https://newsapi.org/v2/everything", params=params).json()
    if res.get('status') == 'ok':
        for art in res.get('articles', []):
            tit = art.get('title', '').lower()
            if not any(x in tit for x in ["fútbol", "deporte", "oscar", "estreno", "artista", "liga", "copa"]):
                noticias.append(art)

print(f"Total found: {len(noticias)}")
for n in noticias[:10]:
    print("-", n['title'])
