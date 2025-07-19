import requests
from bs4 import BeautifulSoup
import argparse
import re

def obtener_titulo_y_imagenes(code):
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
        return {"texto": "", "imagenes": []}

    soup = BeautifulSoup(response.text, "html.parser")

    # 📄 Título desde <head><title>
    titulo = soup.title.string.strip() if soup.title and soup.title.string else "Sin título"

    # 🖼️ Imágenes desde div#thumbnail-gallery
    imagenes = []
    gallery = soup.find("div", id="main-content")
    if gallery:
        thumbs = gallery.find("div", id="thumbnail-gallery")
        if thumbs:
            for div in thumbs.find_all("div", class_="single-thumb"):
                img_tag = div.find("img")
                if img_tag:
                    # Priorizar data-src sobre src si existe
                    src_url = img_tag.get("data-src") or img_tag.get("src")
                    if src_url:
                        # Reemplazar la 't' antes de la extensión (ej. 1t.jpg → 1.jpg)
                        full_img_url = re.sub(r't(?=\.\w{3,4}$)', '', src_url)
                        imagenes.append(full_img_url)

    return {
        "texto": titulo,
        "imagenes": imagenes
    }

# 🎯 CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer título e imágenes HD")
    parser.add_argument("-code", "-C", dest="code", required=True, help="Código de galería")
    args = parser.parse_args()

    datos = obtener_titulo_y_imagenes(args.code)

    print("📄 Título:")
    print(datos["texto"])
    print("\n🖼️ Imágenes HD:")
    for url in datos["imagenes"]:
        print(url)
