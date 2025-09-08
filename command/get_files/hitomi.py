import os
import time
import requests
import hashlib
import zipfile
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def limpiar_nombre(nombre: str) -> str:
    nombre = nombre.replace(" | Hitomi.la", "")
    nombre = re.sub(r'[\\/*?:"<>|]', '', nombre)
    return nombre.strip()

def obtener_titulo_y_autor(link_hitomi: str, chrome_path: str, driver_path: str) -> tuple[str, str]:
    options = Options()
    options.binary_location = chrome_path
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(link_hitomi)
    time.sleep(0.5)

    titulo_completo = driver.title
    driver.quit()

    titulo_limpio = limpiar_nombre(titulo_completo)
    partes = titulo_limpio.split(" by ")
    if len(partes) == 2:
        titulo = partes[0].strip()
        autor = partes[1].strip()
    else:
        titulo = titulo_limpio
        autor = "desconocido"

    return titulo, autor

def truncar_nombre(nombre: str, max_len: int = 63) -> str:
    return nombre[:max_len - 4].strip() + ".cbz"

def descargar_y_comprimir_hitomi(link_hitomi: str) -> str:
    chrome_path = "selenium/chrome-linux64/chrome"
    driver_path = "selenium/chromedriver-linux64/chromedriver"

    if "reader" in link_hitomi:
        id_enlace = link_hitomi.split('/reader/')[1].split('.')[0]
        gallery_link = f"https://hitomi.la/gallery/{id_enlace}.html"
        titulo, autor = obtener_titulo_y_autor(gallery_link, chrome_path, driver_path)
    else:
        titulo, autor = obtener_titulo_y_autor(link_hitomi, chrome_path, driver_path)

    nombre_final = f"{autor} - {titulo}".strip()
    nombre_final = limpiar_nombre(nombre_final)
    nombre_cbz = truncar_nombre(nombre_final)

    carpeta_raiz = os.path.abspath(nombre_final)
    os.makedirs(carpeta_raiz, exist_ok=True)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://hitomi.la/'
    }

    def calcular_hash_imagen(ruta):
        with open(ruta, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def descargar_imagen(url, ruta_destino):
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                with open(ruta_destino, 'wb') as f:
                    f.write(r.content)
                return True
        except:
            pass
        return False

    def extraer_id_enlace(enlace):
        if "reader" in enlace:
            return enlace.split('/reader/')[1].split('.')[0]
        else:
            return enlace.split('-')[-1].split('.')[0]

    id_enlace = extraer_id_enlace(link_hitomi)
    enlace_base = f"https://hitomi.la/reader/{id_enlace}.html"

    options = Options()
    options.binary_location = chrome_path
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    hashes = {}
    duplicados = 0
    contador = 1

    while True:
        url = f"{enlace_base}#{contador}"
        driver.get(url)
        time.sleep(0.1)

        imagenes = driver.find_elements(By.TAG_NAME, 'img')
        urls = [img.get_attribute('src') for img in imagenes if img.get_attribute('src') and img.get_attribute('src').endswith('.webp')]

        if not urls:
            break

        img_url = urls[0]
        nombre_archivo = f"imagen_{contador}.webp"
        ruta_destino = os.path.join(carpeta_raiz, nombre_archivo)

        if descargar_imagen(img_url, ruta_destino):
            hash_actual = calcular_hash_imagen(ruta_destino)
            if hash_actual in hashes.values():
                duplicados += 1
                os.remove(ruta_destino)
                if duplicados >= 3:
                    break
            else:
                hashes[nombre_archivo] = hash_actual
                duplicados = 0

        contador += 1

    driver.quit()

    ruta_cbz = os.path.abspath(nombre_cbz)
    with zipfile.ZipFile(ruta_cbz, 'w') as cbz:
        for root, _, files in os.walk(carpeta_raiz):
            for file in sorted(files):
                ruta_completa = os.path.join(root, file)
                arcname = os.path.relpath(ruta_completa, os.path.dirname(carpeta_raiz))
                cbz.write(ruta_completa, arcname=arcname)

    for file in os.listdir(carpeta_raiz):
        os.remove(os.path.join(carpeta_raiz, file))
    os.rmdir(carpeta_raiz)

    return ruta_cbz
