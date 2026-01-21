import requests
import zipfile
import os
import html
import re
from flask import send_file, after_this_request
from command.get_files.h3_links import obtener_titulo_y_imagenes

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', '', name)

def fetch_images_3hentai(code):
    datos = obtener_titulo_y_imagenes(code, cover=False)
    
    if not datos["imagenes"]:
        return None, []
    
    title = sanitize(html.unescape(datos["texto"]))
    images = datos["imagenes"]
    
    return title, images

def create_3hentai_cbz(code):
    title, images = fetch_images_3hentai(code)
    if not images:
        raise Exception(f"No se encontraron imágenes para el código {code}")
    
    filename = f"{code} - {title}.cbz"
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    
    with zipfile.ZipFile(path, "w") as zipf:
        for i, url in enumerate(images):
            try:
                print(f"📥 Descargando imagen {i+1}/{len(images)}: {url}")
                img = requests.get(url).content
                ext = url.split('.')[-1].split('?')[0]
                fname = f"{i+1}.{ext}"
                temp_path = os.path.join(DOWNLOAD_FOLDER, fname)
                with open(temp_path, "wb") as f: 
                    f.write(img)
                zipf.write(temp_path, fname)
                os.remove(temp_path)
            except Exception as e:
                print(f"Error procesando imagen {url}: {e}")
                continue
    
    return path, filename

def serve_and_clean(filepath):
    filename = os.path.basename(filepath)

    @after_this_request
    def cleanup(resp):
        try:
            os.remove(filepath)
        except:
            pass
        return resp

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.comicbook+zip"
    )
