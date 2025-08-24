import os
import re
import requests
import zipfile
from pathlib import Path

def txt_a_cbz(path_txt):
    path_txt = Path(path_txt).resolve()
    if not path_txt.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path_txt}")

    # Leer contenido
    with open(path_txt, "r", encoding="utf-8", errors="replace") as f:
        lineas = [line.strip() for line in f if line.strip()]

    # Buscar línea que contiene 'URLs de imágenes:'
    idx_urls = next((i for i, line in enumerate(lineas) if "URLs de imágenes:" in line), None)
    if idx_urls is None:
        raise ValueError("No se encontró la sección de URLs de imágenes")

    # Extraer nombre base
    nombre_base = lineas[0]
    nombre_limpio = re.sub(r"[^\w\[\]ñÑ] ", "_", nombre_base, flags=re.UNICODE)
    nombre_limpio = re.sub(r"_+", "_", nombre_limpio).strip("_")
    nombre_cbz = f"{nombre_limpio}.cbz"
    path_cbz = path_txt.parent / nombre_cbz

    # Extraer URLs
    urls = lineas[idx_urls + 1:]
    if not urls:
        raise ValueError("No se encontraron URLs después del marcador")

    # Descargar y empaquetar
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
    }

    with zipfile.ZipFile(path_cbz, "w", compression=zipfile.ZIP_DEFLATED) as cbz:
        for i, url in enumerate(urls, 1):
            try:
                res = requests.get(url, headers=headers, timeout=10)
                res.raise_for_status()
                ext = os.path.splitext(url)[1].lower()
                nombre_img = f"{str(i).zfill(3)}{ext}"
                cbz.writestr(nombre_img, res.content)
            except Exception as e:
                print(f"Error al descargar {url}: {e}")

    # Borrar el .txt
    try:
        os.remove(path_txt)
    except Exception as e:
        print(f"No se pudo borrar el txt: {e}")

    return str(path_cbz)
    