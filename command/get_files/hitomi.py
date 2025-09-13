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
        WebDriverWait(driver, 5).until(
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
    except Exception as e:
        print(f"❌ Error obteniendo título y autor: {str(e)}")
        return "Titulo", "Autor"
    finally:
        driver.quit()

def truncar_nombre(nombre: str, max_len: int = 100) -> str:
    return (nombre[:max_len - 4] + "...") if len(nombre) > max_len else nombre + ".cbz"

def procesar_id_o_enlace(entrada: str) -> tuple[str, str]:
    if entrada.isdigit():
        return f"https://hitomi.la/reader/{entrada}.html", entrada
    if entrada.startswith("https://hitomi.la/"):
        # Convertir URL de galería/manga a URL de reader
        if "/gallery/" in entrada or "/manga/" in entrada:
            match = re.search(r'(\d+)', entrada)
            if match:
                return f"https://hitomi.la/reader/{match.group(1)}.html", match.group(1)
        elif "/reader/" in entrada:
            match = re.search(r'/(\d+)\.html', entrada)
            if match:
                return entrada, match.group(1)
        return entrada, re.search(r'(\d+)', entrada).group(1) if re.search(r'(\d+)', entrada) else "0"
    
    match = re.search(r'(\d+)', entrada)
    if match:
        return f"https://hitomi.la/reader/{match.group(1)}.html", match.group(1)
    
    raise ValueError("Formato de entrada no válido. Debe ser un ID numérico o una URL de Hitomi.la")

def esperar_imagen_cargada(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "img"))
        )
        
        WebDriverWait(driver, timeout).until(
            lambda d: any(
                img.is_displayed() and 
                img.get_attribute('src') and 
                (img.get_attribute('src').endswith('.webp') or 'webp' in img.get_attribute('src') or
                 img.get_attribute('src').endswith('.jpg') or 'jpg' in img.get_attribute('src') or
                 img.get_attribute('src').endswith('.png') or 'png' in img.get_attribute('src'))
                for img in d.find_elements(By.TAG_NAME, 'img')
            )
        )
        return True
    except:
        return False

def descargar_imagen_con_reintentos(url, ruta_destino, headers, max_intentos=5):
    intento = 0
    while intento < max_intentos:
        try:
            response = requests.get(url, headers=headers, timeout=60, stream=True)
            if response.status_code == 200:
                with open(ruta_destino, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                # Verificar que el archivo se descargó correctamente
                if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 0:
                    return True
                else:
                    raise Exception("Archivo descargado vacío o no existe")
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            intento += 1
            tiempo_espera = 3 + (intento * 2)
            print(f"❌ Error descargando imagen (intento {intento}): {str(e)}")
            if intento < max_intentos:
                print(f"⏳ Reintentando en {tiempo_espera} segundos...")
                time.sleep(tiempo_espera)
            # Eliminar archivo corrupto si existe
            if os.path.exists(ruta_destino):
                os.remove(ruta_destino)
    return False

def obtener_url_imagen_pagina(driver, url_pagina, max_intentos=5):
    intento = 0
    while intento < max_intentos:
        try:
            print(f"🌐 Cargando página: {url_pagina}")
            driver.get(url_pagina)
            
            if not esperar_imagen_cargada(driver, timeout=10):
                raise Exception("Timeout esperando imagen")
            
            # Buscar la imagen principal en diferentes elementos
            urls_imagenes = []
            
            # 1. Buscar en elementos picture (prioridad alta)
            picture_elements = driver.find_elements(By.TAG_NAME, 'picture')
            for picture in picture_elements:
                # Buscar source con webp
                sources = picture.find_elements(By.TAG_NAME, 'source')
                for source in sources:
                    srcset = source.get_attribute('srcset')
                    if srcset and ('webp' in srcset or '.webp' in srcset):
                        # Tomar la mejor URL del srcset (última que suele ser la de mayor calidad)
                        urls = [url.strip() for url in srcset.split(',')]
                        for url_desc in urls:
                            if 'webp' in url_desc or '.webp' in url_desc:
                                url_parte = url_desc.split()[0] if ' ' in url_desc else url_desc
                                if url_parte.startswith('//'):
                                    url_parte = 'https:' + url_parte
                                urls_imagenes.append(url_parte)
                
                # Buscar img dentro de picture
                img_elements = picture.find_elements(By.TAG_NAME, 'img')
                for img in img_elements:
                    src = img.get_attribute('src')
                    if src and ('.webp' in src or 'webp' in src):
                        if src.startswith('//'):
                            src = 'https:' + src
                        urls_imagenes.append(src)
            
            # 2. Buscar imágenes directas
            img_elements = driver.find_elements(By.TAG_NAME, 'img')
            for img in img_elements:
                src = img.get_attribute('src')
                if src and ('.webp' in src or 'webp' in src or '.jpg' in src or '.png' in src):
                    if src.startswith('//'):
                        src = 'https:' + src
                    urls_imagenes.append(src)
            
            # 3. Buscar en div de preload
            try:
                preload_div = driver.find_element(By.ID, 'preload')
                preload_imgs = preload_div.find_elements(By.TAG_NAME, 'img')
                for img in preload_imgs:
                    src = img.get_attribute('src')
                    if src and ('.webp' in src or 'webp' in src):
                        if src.startswith('//'):
                            src = 'https:' + src
                        urls_imagenes.append(src)
            except:
                pass
            
            if urls_imagenes:
                # Eliminar duplicados manteniendo el orden
                seen = set()
                unique_urls = []
                for url in urls_imagenes:
                    if url not in seen:
                        seen.add(url)
                        unique_urls.append(url)
                
                # Priorizar URLs que parezcan ser de imágenes principales
                for url in unique_urls:
                    if 'gold-usergeneratedcontent.net' in url and '.webp' in url:
                        print(f"✅ URL encontrada: {url}")
                        return url
                
                # Si no hay URLs de gold-usergeneratedcontent, tomar la primera
                if unique_urls:
                    print(f"✅ URL encontrada: {unique_urls[0]}")
                    return unique_urls[0]
            
            raise Exception("No se encontraron imágenes válidas")
                
        except Exception as e:
            intento += 1
            tiempo_espera = 3 + (intento * 2)
            print(f"❌ Error obteniendo URL de imagen (intento {intento}): {str(e)}")
            if intento < max_intentos:
                print(f"⏳ Reintentando en {tiempo_espera} segundos...")
                time.sleep(tiempo_espera)
    return None

def descargar_y_comprimir_hitomi(entrada: str) -> str:
    try:
        link_hitomi, id_enlace = procesar_id_o_enlace(entrada)
        print(f"🔗 URL procesada: {link_hitomi}")
        print(f"🔢 ID: {id_enlace}")
        
        chrome_path = "selenium/chrome-linux64/chrome"
        driver_path = "selenium/chromedriver-linux64/chromedriver"

        # Obtener título y autor desde la página de galería
        gallery_link = f"https://hitomi.la/gallery/{id_enlace}.html"
        titulo, autor = obtener_titulo_y_autor(gallery_link, chrome_path, driver_path)

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

        # Configurar driver
        options = Options()
        options.binary_location = chrome_path
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--window-size=1920,1080')

        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        hashes = {}
        duplicados_consecutivos = 0
        contador = 1
        max_duplicados_consecutivos = 10  # Detener después de 10 duplicados seguidos
        imagenes_descargadas = 0

        print("🚀 Iniciando descarga de imágenes...")

        while duplicados_consecutivos < max_duplicados_consecutivos:
            url_pagina = f"https://hitomi.la/reader/{id_enlace}.html#{contador}"
            print(f"📖 Página {contador}: {url_pagina}")
            
            img_url = obtener_url_imagen_pagina(driver, url_pagina)
            if not img_url:
                print(f"❌ No se pudo obtener URL para página {contador}")
                duplicados_consecutivos += 1
                contador += 1
                continue
            
            # Determinar extensión del archivo
            if '.webp' in img_url:
                extension = '.webp'
            elif '.jpg' in img_url or '.jpeg' in img_url:
                extension = '.jpg'
            elif '.png' in img_url:
                extension = '.png'
            else:
                extension = '.webp'  # default
            
            nombre_archivo = f"{contador:04d}{extension}"
            ruta_destino = os.path.join(carpeta_temporal, nombre_archivo)

            if descargar_imagen_con_reintentos(img_url, ruta_destino, headers):
                # Verificar si la imagen es duplicada
                if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 0:
                    hash_actual = calcular_hash_imagen(ruta_destino)
                    if hash_actual in hashes.values():
                        print(f"⚠️  Imagen duplicada: {nombre_archivo}")
                        duplicados_consecutivos += 1
                        os.remove(ruta_destino)
                        if duplicados_consecutivos >= max_duplicados_consecutivos:
                            print("🛑 Demasiadas imágenes duplicadas consecutivas, finalizando descarga")
                            break
                    else:
                        hashes[nombre_archivo] = hash_actual
                        duplicados_consecutivos = 0
                        imagenes_descargadas += 1
                        print(f"✅ Descargada: {nombre_archivo} ({imagenes_descargadas} imágenes)")
                else:
                    print(f"❌ Archivo vacío o corrupto: {nombre_archivo}")
                    duplicados_consecutivos += 1
            else:
                print(f"❌ Error al descargar: {nombre_archivo}")
                duplicados_consecutivos += 1
            
            contador += 1
            time.sleep(1)  # Esperar entre páginas

        driver.quit()

        archivos_descargados = [f for f in os.listdir(carpeta_temporal) if os.path.isfile(os.path.join(carpeta_temporal, f))]
        if not archivos_descargados:
            print("❌ No se descargaron imágenes. Eliminando carpeta temporal.")
            os.rmdir(carpeta_temporal)
            return ""

        print(f"✅ Descargadas {imagenes_descargadas} imágenes correctamente")

        # Crear archivo CBZ
        ruta_cbz = os.path.join(BASE_DIR, nombre_cbz)
        with zipfile.ZipFile(ruta_cbz, 'w', zipfile.ZIP_DEFLATED) as cbz:
            for file in sorted(archivos_descargados):
                ruta_completa = os.path.join(carpeta_temporal, file)
                arcname = os.path.join(nombre_final, file)
                cbz.write(ruta_completa, arcname=arcname)

        # Limpiar carpeta temporal
        for file in archivos_descargados:
            os.remove(os.path.join(carpeta_temporal, file))
        os.rmdir(carpeta_temporal)

        print(f"✅ Archivo CBZ creado: {ruta_cbz}")
        print(f"📦 Tamaño: {os.path.getsize(ruta_cbz) / (1024*1024):.2f} MB")
        return ruta_cbz

    except Exception as e:
        print(f"❌ Error fatal en el proceso: {str(e)}")
        return ""

if __name__ == "__main__":
    buscar = input()
    resultado = descargar_y_comprimir_hitomi(buscar)
    if resultado:
        print(f"🎉 Proceso completado: {resultado}")
    else:
        print("Algo fallo")
