import os
import requests
from PIL import Image, ImageDraw, ImageFont

def get_font(url, filename="font.ttf"):
    if not os.path.exists(filename):
        r = requests.get(url)
        with open(filename, 'wb') as f:
            f.write(r.content)
    return filename

font_url = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Bold.ttf"
font_path = get_font(font_url, "Montserrat-Bold.ttf")

bg_path = "/Users/elthomas/.gemini/antigravity/brain/d3ca2165-4572-4da6-9742-68a6ea5b70c3/fondo_lovart_demo_1774626718808.png"
out_path = "/Users/elthomas/.gemini/antigravity/brain/d3ca2165-4572-4da6-9742-68a6ea5b70c3/maqueta_cripgold.png"

# Configuracion Canvas
width, height = 1080, 1350
img = Image.open(bg_path).convert("RGBA")

# Resize dinamico a proporcion Instagram Vertical
img_ratio = img.width / img.height
target_ratio = width / height
if img_ratio > target_ratio:
    new_h = height
    new_w = int(new_h * img_ratio)
else:
    new_w = width
    new_h = int(new_w / img_ratio)

img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
left = (img.width - width) / 2
top = (img.height - height) / 2
img = img.crop((left, top, left + width, top + height))

# Capa de oscurecimiento sutil para resaltar el texto
overlay = Image.new('RGBA', img.size, (0, 20, 10, 160))
img = Image.alpha_composite(img, overlay)
draw = ImageDraw.Draw(img)

# Configuracion del Título (Noticia Ficticia)
font_size = 75
font = ImageFont.truetype(font_path, font_size)
text = "EL PRECIO DEL ORO\nALCANZA NUEVOS\nMÁXIMOS HISTÓRICOS Y ES \nLA MEJOR INVERSIÓN DEL 2026"

# Calculos matematicos para centrar perfecto
bbox = draw.multiline_textbbox((0,0), text, font=font, align="center")
w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
x = (width - w) / 2
y = (height - h) / 2 - 50 # Un poco arriba del medio

# Dibujar sombra (shadow) y texto
draw.multiline_text((x+4, y+4), text, fill=(0, 0, 0, 150), font=font, align="center")
draw.multiline_text((x, y), text, fill=(255, 245, 215), font=font, align="center")

# Mock de Logo
logo_font = ImageFont.truetype(font_path, 40)
draw.text((70, height - 120), "CripGold.", fill=(200, 170, 50), font=logo_font) # Gold color

# Categoria Superior
header_font = ImageFont.truetype(font_path, 30)
draw.text((x, y - 80), "NOTICIAS / MERCADO", fill=(0, 255, 127), font=header_font)

# Guardar
img.convert('RGB').save(out_path)
print("OK. Imagen generada.")
