import requests
from bs4 import BeautifulSoup
import argparse
import os
import re  # ✅ Añadido para usar re.sub

def obtener_info_y_links(code, cover=False):
    base_url = f"https://nhentai.website/g/{code}"
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

    # 🔍 Buscar contenedor de thumbnails
    thumbs_container = soup.find("div", id="thumbnail-container")
    thumb_divs = thumbs_container.find_all("div", class_="thumb-container") if thumbs_container else []
    total_paginas = len(thumb_divs)

    imagenes = []
    if cover:
        thumb_divs = thumb_divs[:1]

    for div in thumb_divs:
        img_tag = div.find("img", class_="lazyload")
        if img_tag:
            src_url = img_tag.get("data-src")
            if src_url:
                # 🔧 Eliminar la 'x' justo antes de la extensión
                src_url = re.sub(r'x(?=\.(jpg|jpeg|png|webp|gif)$)', '', src_url, flags=re.IGNORECASE)
                imagenes.append(src_url)

    return {
        "texto": titulo,
        "imagenes": imagenes,
        "total_paginas": total_paginas
    }

def guardar_como_txt(datos, code):
    nombre_archivo = f"{code}.txt"
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(f"Título: {datos['texto']}\n")
            f.write(f"Total de páginas: {datos['total_paginas']}\n\n")
            f.write("Imágenes HD:\n")
            for url in datos["imagenes"]:
                f.write(url + "\n")
        print(f"\n📝 Archivo guardado como: {nombre_archivo}")
    except Exception as e:
        print("❌ Error al guardar TXT:", e)

# 🎯 CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer título e imágenes HD de nhentai.website")
    parser.add_argument("-code", "-C", dest="code", required=True, help="Código de galería")
    parser.add_argument("--cover", action="store_true", help="Solo extraer portada")
    parser.add_argument("--txt", action="store_true", help="Guardar salida como .txt")
    args = parser.parse_args()

    datos = obtener_titulo_y_imagenes(args.code, cover=args.cover)

    print("📄 Título:")
    print(datos["texto"])
    print(f"\n🧮 Total de páginas: {datos['total_paginas']}")
    print("\n🖼️ Imágenes HD:")
    for url in datos["imagenes"]:
        print(url)

    if args.txt:
        guardar_como_txt(datos, args.code)
