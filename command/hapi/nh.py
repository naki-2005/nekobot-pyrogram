import os
import re
import zipfile
import html
import requests
from command.get_files.nh_selenium import scrape_nhentai

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', '', name)

def create_nhentai_cbz(code):
    result = scrape_nhentai(code)
    title = result["title"]
    images = result["links"]
    
    if not images:
        raise Exception(f"No se encontraron imágenes para el código nhentai {code}")
    
    sanitized_title = sanitize(html.unescape(title))
    
    filename = f"{code} - {sanitized_title}.cbz"
    path = os.path.join(DOWNLOAD_FOLDER, filename)
    
    with zipfile.ZipFile(path, "w") as zipf:
        for i, url in enumerate(images):
            try:
                print(f"📥 Descargando imagen {i+1}/{len(images)}...")
                img_data = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                    "Referer": "https://nhentai.net/"
                }).content
                
                ext = url.split('.')[-1].split('?')[0]
                fname = f"{i+1:03d}.{ext}"
                temp_path = os.path.join(DOWNLOAD_FOLDER, fname)
                
                with open(temp_path, "wb") as f: 
                    f.write(img_data)
                zipf.write(temp_path, fname)
                os.remove(temp_path)
                
            except Exception as e:
                print(f"❌ Error procesando imagen {url}: {e}")
                continue
    
    print(f"✅ CBZ creado exitosamente: {filename}")
    return path, filename
