import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse


import re

def limpiar_nombre_para_archivo(nombre_raw):
    nombre_limpio = re.sub(r"[^\w\[\]ñÑ]", "_", nombre_raw, flags=re.UNICODE)
    nombre_limpio = re.sub(r"_+", "_", nombre_limpio).strip("_")
    return nombre_limpio
    
def obtener_info_y_links(code, cover=False):
    web_1 = "https://nhentai.website"
    base_url = f"{web_1}/g/{code}"
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
        print("❌ Error:", e)
        return {"texto": "", "imagenes": [], "total_paginas": 0}

    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.find("div", id="content")
    if not content:
        return {"texto": "", "imagenes": [], "total_paginas": 0}

    texto_final = []
    info_div = content.find("div", id="bigcontainer")
    if info_div:
        info_block = info_div.find("div", id="info-block")
        if info_block:
            info = info_block.find("div", id="info")
            if info:
                for h in ["h1", "h2", "h3"]:
                    encabezado = info.find(h, class_="title")
                    if encabezado:
                        partes = []
                        for clase in ["before", "pretty", "after"]:
                            span = encabezado.find("span", class_=clase)
                            if span and span.text.strip():
                                partes.append(span.text.strip())
                        if partes:
                            texto_final.append(" ".join(partes))

    thumbnail_container = content.find("div", id="thumbnail-container")
    thumbs = thumbnail_container.find("div", class_="thumbs") if thumbnail_container else None
    thumb_divs = thumbs.find_all("div", class_="thumb-container") if thumbs else []
    total_paginas = len(thumb_divs)

    if cover:
        primera_pagina = f"{web_1}/g/{code}/1/"
        try:
            res = requests.get(primera_pagina, headers=headers, timeout=10)
            res.raise_for_status()
            sub_soup = BeautifulSoup(res.text, "html.parser")
            section = sub_soup.find("section", id="image-container")
            if section:
                img_tag = section.find("img")
                if img_tag and img_tag.get("src"):
                    img_url = urljoin(web_1, img_tag["src"])
                    return {
                        "texto": "\n".join(texto_final),
                        "imagenes": [img_url],
                        "total_paginas": total_paginas
                    }
        except requests.exceptions.RequestException:
            pass

        return {
            "texto": "\n".join(texto_final),
            "imagenes": [],
            "total_paginas": total_paginas
        }

    imagenes = []
    for i in range(1, total_paginas + 1):
        pagina_url = f"{web_1}/g/{code}/{i}/"
        try:
            res = requests.get(pagina_url, headers=headers, timeout=10)
            res.raise_for_status()
        except requests.exceptions.RequestException:
            continue

        sub_soup = BeautifulSoup(res.text, "html.parser")
        section = sub_soup.find("div", id="content")
        if section:
            section_img = section.find("section", id="image-container")
            if section_img:
                img_tag = section_img.find("img")
                if img_tag and img_tag.get("src"):
                    img_url = urljoin(web_1, img_tag["src"])
                    imagenes.append(img_url)

    return {
        "texto": "\n".join(texto_final),
        "imagenes": imagenes,
        "total_paginas": total_paginas
    }

# 🎯 CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obtener texto e imágenes por código")
    parser.add_argument("-code", "-C", dest="code", required=True, help="Código del recurso")
    parser.add_argument("--cover", action="store_true", help="Solo obtener portada")
    parser.add_argument("-txt", "-T", dest="guardar_txt", action="store_true", help="Guardar información textual en archivo .txt")
    args = parser.parse_args()

    datos = obtener_info_y_links(args.code, cover=args.cover)

    print("📄 Información textual:")
    print(datos["texto"])
    print(f"\n🧮 Total de páginas: {datos['total_paginas']}")
    print("\n🖼️ URLs de imágenes:")
    for url in datos["imagenes"]:
        print(url)

    if args.guardar_txt and datos["texto"].strip():
        nombre_base = datos["texto"].split("\n")[0] if datos["texto"] else f"code_{args.code}"
        nombre_archivo = limpiar_nombre_para_archivo(nombre_base) + ".txt"

        try:
            with open(nombre_archivo, "w", encoding="utf-8") as f:
                f.write(datos["texto"].strip() + "\n\n")
                f.write(f"🧮 Total de páginas: {datos['total_paginas']}\n")
                f.write("🖼️ URLs de imágenes:\n")
                for url in datos["imagenes"]:
                    f.write(url + "\n")
            print(f"\n✅ Archivo guardado como: {nombre_archivo}")
        except Exception as e:
            print(f"\n❌ Error al guardar archivo: {e}")
            