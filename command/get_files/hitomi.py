import os
import time
import requests
import hashlib
import zipfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

def descargar_y_comprimir_hitomi(link_hitomi: str) -> str:
    # 📁 Preparar entorno
    carpeta_imagenes = 'imagenes'
    os.makedirs(carpeta_imagenes, exist_ok=True)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://hitomi.la/'
    }

    def calcular_hash_imagen(ruta):
        with open(ruta, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def descargar_imagen(url, nombre):
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                with open(os.path.join(carpeta_imagenes, nombre), 'wb') as f:
                    f.write(r.content)
                return True
        except:
            pass
        return False

    def ajustar_enlace(enlace):
        id_enlace = enlace.split('-')[-1].split('.')[0]
        return f"https://hitomi.la/reader/{id_enlace}.html"

    # 🧠 Configurar Selenium
    chrome_path = "selenium/chrome-linux64/chrome"
    driver_path = "selenium/chromedriver-linux64/chromedriver"
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.binary_location = chrome_path
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    # 🔗 Preparar enlace
    enlace_base = ajustar_enlace(link_hitomi)
    hashes = {}
    duplicados = 0
    contador = 1

    # 🔁 Descargar imágenes
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
        ruta = os.path.join(carpeta_imagenes, nombre_archivo)

        if descargar_imagen(img_url, nombre_archivo):
            hash_actual = calcular_hash_imagen(ruta)
            if hash_actual in hashes.values():
                duplicados += 1
                os.remove(ruta)
                if duplicados >= 3:
                    break
            else:
                hashes[nombre_archivo] = hash_actual
                duplicados = 0

        contador += 1

    driver.quit()

    # 📦 Comprimir a CBZ
    nombre_cbz = f"hitomi_{int(time.time())}.cbz"
    ruta_cbz = os.path.abspath(nombre_cbz)
    with zipfile.ZipFile(ruta_cbz, 'w') as cbz:
        for nombre in sorted(os.listdir(carpeta_imagenes)):
            ruta_img = os.path.join(carpeta_imagenes, nombre)
            cbz.write(ruta_img, arcname=nombre)

    # 🧹 Limpiar imágenes
    for nombre in os.listdir(carpeta_imagenes):
        os.remove(os.path.join(carpeta_imagenes, nombre))
    os.rmdir(carpeta_imagenes)

    return ruta_cbz
