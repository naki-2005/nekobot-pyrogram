import os
import time
import requests
import hashlib
import zipfile
import re
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json

BASE_DIR = "vault_files/doujins"

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
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(link_hitomi)
        WebDriverWait(driver, 2).until(
            lambda d: d.title and d.title.strip() != "" and "Hitomi.la" in d.title
        )

        titulo_completo = driver.title
        titulo_limpio = limpiar_nombre(titulo_completo)
        partes = titulo_limpio.split(" by ")
        
        if len(partes) == 2:
            titulo = partes[0].strip()
            autor = partes[1].strip()
        else:
            titulo = titulo_limpio
            autor = "desconocido"
            
        return titulo, autor
    finally:
        driver.quit()

def truncar_nombre(nombre: str, max_len: int = 63) -> str:
    return (nombre[:max_len - 4] + "...") if len(nombre) > max_len else nombre + ".cbz"

def procesar_id_o_enlace(entrada: str) -> str:
    if entrada.isdigit():
        return f"https://hitomi.la/reader/{entrada}.html"
    if entrada.startswith("https://hitomi.la/"):
        return entrada
    match = re.search(r'(\d+)', entrada)
    if match:
        return f"https://hitomi.la/reader/{match.group(1)}.html"
    
    raise ValueError("Formato de entrada no válido. Debe ser un ID numérico o una URL de Hitomi.la")

def extraer_urls_imagenes_directas(driver, url):
    """Extrae URLs de imágenes WebP directamente del HTML"""
    driver.get(url)
    time.sleep(3)
    
    # Obtener el HTML después de que se cargue la página
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, 'html.parser')
    
    image_urls = []
    
    # Buscar todas las imágenes WebP en la página principal
    for img in soup.find_all('img', src=True):
        src = img['src']
        if src.endswith('.webp'):
            if src.startswith('//'):
                src = 'https:' + src
            elif not src.startswith('http'):
                src = 'https://hitomi.la' + src
            image_urls.append(src)
    
    # Buscar en elementos picture (que contienen source con AVIF y WebP)
    for picture in soup.find_all('picture'):
        # Buscar source con WebP
        webp_source = picture.find('source', srcset=True, type=lambda x: x and 'webp' in x if x else False)
        if webp_source:
            srcset = webp_source['srcset']
            # Tomar la primera URL del srcset (puede contener múltiples URLs con descriptores)
            if ' ' in srcset:
                url_part = srcset.split()[0]
            else:
                url_part = srcset
            
            if url_part.startswith('//'):
                url_part = 'https:' + url_part
            elif not url_part.startswith('http'):
                url_part = 'https://hitomi.la' + url_part
            
            image_urls.append(url_part)
        
        # También buscar img dentro de picture como respaldo
        img_in_picture = picture.find('img', src=True)
        if img_in_picture and img_in_picture['src'].endswith('.webp'):
            src = img_in_picture['src']
            if src.startswith('//'):
                src = 'https:' + src
            elif not src.startswith('http'):
                src = 'https://hitomi.la' + src
            image_urls.append(src)
    
    # Eliminar duplicados manteniendo el orden
    seen = set()
    unique_urls = []
    for url in image_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    return unique_urls

def descargar_imagen_con_reintentos(url, ruta_destino, headers, max_intentos=3):
    intento = 0
    while intento < max_intentos:
        try:
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            if response.status_code == 200:
                with open(ruta_destino, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            intento += 1
            tiempo_espera = 2 + intento
            print(f"❌ Error descargando imagen (intento {intento}): {str(e)}")
            if intento < max_intentos:
                print(f"⏳ Reintentando en {tiempo_espera} segundos...")
                time.sleep(tiempo_espera)
    return False

def descargar_y_comprimir_hitomi(entrada: str) -> str:
    link_hitomi = procesar_id_o_enlace(entrada)
    
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

    os.makedirs(BASE_DIR, exist_ok=True)
    carpeta_temporal = os.path.join(BASE_DIR, str(uuid.uuid4()))
    os.makedirs(carpeta_temporal, exist_ok=True)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://hitomi.la/',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
    }

    def calcular_hash_imagen(ruta):
        with open(ruta, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    # Configurar driver para extracción directa
    options = Options()
    options.binary_location = chrome_path
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    # Extraer URLs de imágenes directamente
    print("🔍 Extrayendo URLs de imágenes WebP...")
    image_urls = extraer_urls_imagenes_directas(driver, link_hitomi)
    
    if not image_urls:
        print("❌ No se encontraron imágenes WebP en la página")
        driver.quit()
        return ""
    
    print(f"📷 Encontradas {len(image_urls)} imágenes WebP")
    
    # Descargar imágenes
    hashes = {}
    success_count = 0
    
    for i, img_url in enumerate(image_urls):
        print(f"⬇️  Descargando imagen {i+1}/{len(image_urls)}")
        
        nombre_archivo = f"{i+1:03d}.webp" 
        ruta_destino = os.path.join(carpeta_temporal, nombre_archivo)

        if descargar_imagen_con_reintentos(img_url, ruta_destino, headers):
            # Verificar si la imagen es duplicada
            hash_actual = calcular_hash_imagen(ruta_destino)
            if hash_actual in hashes.values():
                print(f"⚠️  Imagen duplicada encontrada: {nombre_archivo}")
                os.remove(ruta_destino)
            else:
                hashes[nombre_archivo] = hash_actual
                success_count += 1
                print(f"✅ Descargada: {nombre_archivo}")
        else:
            print(f"❌ Error al descargar imagen {i+1}")
        
        time.sleep(1)  # Esperar entre descargas

    driver.quit()

    archivos_descargados = [f for f in os.listdir(carpeta_temporal) if os.path.isfile(os.path.join(carpeta_temporal, f))]
    if not archivos_descargados:
        print("❌ No se descargaron imágenes. Eliminando carpeta temporal.")
        os.rmdir(carpeta_temporal)
        return ""

    print(f"✅ Descargadas {success_count}/{len(image_urls)} imágenes correctamente")

    # Crear archivo CBZ
    ruta_cbz = os.path.join(BASE_DIR, nombre_cbz)
    with zipfile.ZipFile(ruta_cbz, 'w') as cbz:
        for root, _, files in os.walk(carpeta_temporal):
            for file in sorted(files):
                ruta_completa = os.path.join(root, file)
                arcname = os.path.join(nombre_final, file)
                cbz.write(ruta_completa, arcname=arcname)

    # Limpiar carpeta temporal
    for file in os.listdir(carpeta_temporal):
        os.remove(os.path.join(carpeta_temporal, file))
    os.rmdir(carpeta_temporal)

    print(f"✅ Archivo CBZ creado: {ruta_cbz}")
    return ruta_cbz
