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

def esperar_imagen_cargada(driver, timeout=2):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "img"))
        )
        
        WebDriverWait(driver, timeout).until(
            lambda d: any(
                img.is_displayed() and 
                img.get_attribute('src') and 
                (img.get_attribute('src').endswith('.webp') or 'webp' in img.get_attribute('src'))
                for img in d.find_elements(By.TAG_NAME, 'img')
            )
        )
        return True
    except:
        return False

def descargar_imagen_con_reintentos(url, ruta_destino, headers, max_intentos=float('inf')):
    intento = 0
    while intento < max_intentos:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                with open(ruta_destino, 'wb') as f:
                    f.write(r.content)
                return True
            else:
                raise Exception(f"HTTP {r.status_code}")
        except Exception as e:
            intento += 1
            tiempo_espera = 3 + intento
            print(f"❌ Error descargando imagen (intento {intento}): {str(e)}")
            print(f"⏳ Reintentando en {tiempo_espera} segundos...")
            time.sleep(tiempo_espera)
    return False

def obtener_url_imagen_con_reintentos(driver, url_pagina, max_intentos=float('inf')):
    intento = 0
    while intento < max_intentos:
        try:
            driver.get(url_pagina)
            
            if not esperar_imagen_cargada(driver, timeout=2):
                raise Exception("Timeout esperando imagen")
            
            imagenes = driver.find_elements(By.TAG_NAME, 'img')
            urls_webp = [
                img.get_attribute('src') for img in imagenes 
                if (img.get_attribute('src') and 
                    (img.get_attribute('src').endswith('.webp') or 
                     'webp' in img.get_attribute('src')))
            ]
            
            if urls_webp:
                return urls_webp[0]
            else:
                raise Exception("No se encontraron imágenes webp")
                
        except Exception as e:
            intento += 1
            tiempo_espera = 3 + intento
            print(f"❌ Error obteniendo URL de imagen (intento {intento}): {str(e)}")
            print(f"⏳ Reintentando en {tiempo_espera} segundos...")
            time.sleep(tiempo_espera)
    return None

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
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    hashes = {}
    duplicados = 0
    contador = 1
    max_paginas_sin_progreso = 5
    paginas_sin_progreso = 0

    while paginas_sin_progreso < max_paginas_sin_progreso:
        url_pagina = f"{enlace_base}#{contador}"
        print(f"🔄 Procesando página {contador}")
        
        img_url = obtener_url_imagen_con_reintentos(driver, url_pagina)
        if not img_url:
            print(f"❌ No se pudo obtener URL para página {contador}")
            paginas_sin_progreso += 1
            contador += 1
            continue
            
        nombre_archivo = f"{contador:03d}.webp" 
        ruta_destino = os.path.join(carpeta_temporal, nombre_archivo)

        if descargar_imagen_con_reintentos(img_url, ruta_destino, headers):
            hash_actual = calcular_hash_imagen(ruta_destino)
            if hash_actual in hashes.values():
                print(f"⚠️  Imagen duplicada encontrada: {nombre_archivo}")
                duplicados += 1
                os.remove(ruta_destino)
                if duplicados >= 3:
                    print("🛑 Demasiadas imágenes duplicadas consecutivas, finalizando descarga")
                    break
            else:
                hashes[nombre_archivo] = hash_actual
                duplicados = 0
                paginas_sin_progreso = 0
                print(f"✅ Descargada página {contador}")
        else:
            print(f"❌ Error al descargar página {contador}")
            paginas_sin_progreso += 1
        
        contador += 1

    driver.quit()

    archivos_descargados = [f for f in os.listdir(carpeta_temporal) if os.path.isfile(os.path.join(carpeta_temporal, f))]
    if not archivos_descargados:
        print("❌ No se descargaron imágenes. Eliminando carpeta temporal.")
        os.rmdir(carpeta_temporal)
        return ""

    ruta_cbz = os.path.join(BASE_DIR, nombre_cbz)
    with zipfile.ZipFile(ruta_cbz, 'w') as cbz:
        for root, _, files in os.walk(carpeta_temporal):
            for file in sorted(files):
                ruta_completa = os.path.join(root, file)
                arcname = os.path.join(nombre_final, file)
                cbz.write(ruta_completa, arcname=arcname)

    for file in os.listdir(carpeta_temporal):
        os.remove(os.path.join(carpeta_temporal, file))
    os.rmdir(carpeta_temporal)

    print(f"✅ Archivo CBZ creado: {ruta_cbz}")
    return ruta_cbz
