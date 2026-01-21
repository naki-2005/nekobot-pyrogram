import requests
from bs4 import BeautifulSoup
import argparse
import re
import os

def obtener_titulo_y_imagenes(code, cover=False):
    web_1 = "https://es.3hentai.net"
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
        return {"texto": "", "imagenes": [], "total_paginas": 0, "tags": {}}

    soup = BeautifulSoup(response.text, "html.parser")
    titulo = soup.title.string.strip() if soup.title and soup.title.string else "Sin título"

    gallery = soup.find("div", id="main-content")
    thumbs = gallery.find("div", id="thumbnail-gallery") if gallery else None
    thumb_divs = thumbs.find_all("div", class_="single-thumb") if thumbs else []
    total_paginas = len(thumb_divs)

    tags_dict = {}
    tag_containers = soup.find_all("div", class_="tag-container")
    for container in tag_containers:
        field_name = container.get_text(strip=True).split(':')[0].strip()
        tags = []
        for tag_link in container.find_all("a", class_="name"):
            tags.append(tag_link.get_text(strip=True))
        if tags:
            tags_dict[field_name] = tags

    imagenes = []
    if cover:
        if thumb_divs:
            img_tag = thumb_divs[0].find("img")
            if img_tag:
                src_url = img_tag.get("data-src") or img_tag.get("src")
                if src_url:
                    full_img_url = re.sub(r't(?=\.\w{3,4}$)', '', src_url)
                    imagenes.append(full_img_url)
    else:
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
        "total_paginas": total_paginas,
        "tags": tags_dict
    }

def guardar_como_txt(datos, code):
    nombre_archivo = f"{code}.txt"
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(f"Título: {datos['texto']}\n")
            f.write(f"Total de páginas: {datos['total_paginas']}\n\n")
            
            if datos['tags']:
                f.write("TAGS:\n")
                for categoria, tags in datos['tags'].items():
                    f.write(f"{categoria}: {', '.join(tags)}\n")
                f.write("\n")
            
            f.write("Imágenes HD:\n")
            for url in datos["imagenes"]:
                f.write(url + "\n")
        print(f"\n📝 Archivo guardado como: {nombre_archivo}")
    except Exception as e:
        print("❌ Error al guardar TXT:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer título e imágenes HD")
    parser.add_argument("-code", "-C", dest="code", required=True, help="Código de galería")
    parser.add_argument("--cover", action="store_true", help="Solo extraer portada")
    parser.add_argument("--txt", action="store_true", help="Guardar salida como .txt")
    parser.add_argument("--tags", action="store_true", help="Mostrar tags en la salida")
    args = parser.parse_args()

    datos = obtener_titulo_y_imagenes(args.code, cover=args.cover)

    print("📄 Título:")
    print(datos["texto"])
    print(f"\n🧮 Total de páginas: {datos['total_paginas']}")
    
    if args.tags and datos['tags']:
        print("\n🏷️ TAGS:")
        for categoria, tags in datos['tags'].items():
            print(f"{categoria}: {', '.join(tags)}")
    
    print("\n🖼️ Imágenes HD:")
    for url in datos["imagenes"]:
        print(url)

    if args.txt:
        guardar_como_txt(datos, args.code)
