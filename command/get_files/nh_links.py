import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse

def obtener_info_y_links(code, cover=False):
    web_1 = "https://nhentai.net"

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
        return {"texto": "", "imagenes": []}

    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.find("div", id="content")
    if not content:
        return {"texto": "", "imagenes": []}

    # 🧠 Extraer texto
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

    # 🖼️ Obtener una sola imagen si es COVER
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
                    return {"texto": "\n".join(texto_final), "imagenes": [img_url]}
        except requests.exceptions.RequestException:
            return {"texto": "\n".join(texto_final), "imagenes": []}

        return {"texto": "\n".join(texto_final), "imagenes": []}

    # 🖼️ Obtener todas las imágenes si NO es cover
    imagenes = []
    thumbnail_container = content.find("div", id="thumbnail-container")
    thumbs = thumbnail_container.find("div", class_="thumbs") if thumbnail_container else None
    thumb_divs = thumbs.find_all("div", class_="thumb-container") if thumbs else []
    total = len(thumb_divs)

    for i in range(1, total + 1):
        pagina_url = f"{web_1}/g/{code}/{i}/"
        try:
            res = requests.get(pagina_url, headers=headers, timeout=10)
            res.raise_for_status()
        except requests.exceptions.RequestException:
            continue

        sub_soup = BeautifulSoup(res.text, "html.parser")
        section = sub_soup.find("section", id="image-container")
        if section:
            img_tag = section.find("img")
            if img_tag and img_tag.get("src"):
                img_url = urljoin(web_1, img_tag["src"])
                imagenes.append(img_url)

    return {
        "texto": "\n".join(texto_final),
        "imagenes": imagenes
    }

# 🎯 CLI de prueba
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obtener texto e imágenes por código")
    parser.add_argument("-code", "-C", dest="code", required=True, help="Código del recurso")
    parser.add_argument("--cover", action="store_true", help="Solo obtener portada")
    args = parser.parse_args()

    datos = obtener_info_y_links(args.code, cover=args.cover)

    print("📄 Información textual:")
    print(datos["texto"])
    print("\n🖼️ URLs de imágenes:")
    for url in datos["imagenes"]:
        print(url)
