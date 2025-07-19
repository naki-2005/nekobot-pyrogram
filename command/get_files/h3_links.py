import requests
from bs4 import BeautifulSoup
import argparse
import re

def obtener_titulo_y_imagenes(code, cover=False):
    web_1 = "https://es.3hentai.net"  # ← Reemplaza por tu sitio base
    base_url = f"{web_1}/d/{code}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("❌ Error al conectar:", e)
        return {"texto": "", "imagenes": [], "total_paginas": 0}

    soup = BeautifulSoup(response.text, "html.parser")

    # 📄 Título desde <head><title>
    titulo = soup.title.string.strip() if soup.title and soup.title.string else "Sin título"

    # 🔢 Contar total de thumbnails como páginas
    gallery = soup.find("div", id="main-content")
    thumbs = gallery.find("div", id="thumbnail-gallery") if gallery else None
    thumb_divs = thumbs.find_all("div", class_="single-thumb") if thumbs else []
    total_paginas = len(thumb_divs)

    # ⚡ Modo portada → obtener solo una imagen
    if cover:
        if thumbs and thumb_divs:
            img_tag = thumb_divs[0].find("img")
            if img_tag:
                src_url = img_tag.get("data-src") or img_tag.get("src")
                if src_url:
                    full_img_url = re.sub(r't(?=\.\w{3,4}$)', '', src_url)
                    return {
                        "texto": titulo,
                        "imagenes": [full_img_url],
                        "total_paginas": total_paginas
                    }
        return {"texto": titulo, "imagenes": [], "total_paginas": total_paginas}

    # 📦 Extraer todas las imágenes
    imagenes = []
    for div in thumb_divs:
        img_tag = div.find("img")
        if img_tag:
            src_url = img_tag.get("data-src") or img_tag.get("src")
            if src_url:
                full_img_url = re.sub(r't(?=\.\w{3,4}$)', '', src_url)
                imagenes.append(full_img_url)

    return {
        "texto": titulo,
        "imagenes": imagenes,
        "total_paginas": total_paginas
    }

# 🎯 CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer título e imágenes HD")
    parser.add_argument("-code", "-C", dest="code", required=True, help="Código de galería")
    parser.add_argument("--cover", action="store_true", help="Solo extraer portada")
    args = parser.parse_args()

    datos = obtener_titulo_y_imagenes(args.code, cover=args.cover)

    print("📄 Título:")
    print(datos["texto"])
    print(f"\n🧮 Total de páginas: {datos['total_paginas']}")
    print("\n🖼️ Imágenes HD:")
    for url in datos["imagenes"]:
        print(url)
