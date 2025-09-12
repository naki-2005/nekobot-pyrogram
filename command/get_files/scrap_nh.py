import argparse
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

CHROME_BINARY_PATH = "selenium/chrome-linux64/chrome"
CHROMEDRIVER_PATH = "selenium/chromedriver-linux64/chromedriver"

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
    chrome_options.add_argument('--accept-language=en-US,en;q=0.9')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    chrome_options.binary_location = CHROME_BINARY_PATH
    chromedriver_path = CHROMEDRIVER_PATH

    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"Error al configurar el driver: {e}")
        return None

def scrape_nhentai_with_selenium(search_term, page=1):
    driver = setup_driver()
    if not driver:
        return []
    
    try:
        url = f"https://nhentai.net/search/?q={search_term}&page={page}"
        print(f"Accediendo a: {url}")
        
        driver.get(url)
        time.sleep(5)
        
        if "Just a moment" in driver.page_source or "Verifying" in driver.page_source:
            print("Esperando a que Cloudflare verifique...")
            time.sleep(10)
        
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "gallery"))
            )
        except:
            print("No se encontraron galleries o timeout esperando")
            return []
        
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        gallery_divs = soup.find_all('div', class_='gallery')
        
        if not gallery_divs:
            print("No se encontraron galleries")
            return []
        
        print(f"Encontrados {len(gallery_divs)} galleries")
        results = []
        
        for gallery in gallery_divs:
            try:
                data_tags = gallery.get('data-tags', '').split()
                link_tag = gallery.find('a', class_='cover')
                if not link_tag:
                    continue
                
                href = link_tag.get('href', '')
                gallery_code = href.split('/')[-2] if href.startswith('/g/') else 'N/A'
                
                img_tags = gallery.find_all('img')
                image_links = []
                
                for img in img_tags:
                    src = img.get('src', '') or img.get('data-src', '')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://nhentai.net' + src
                        image_links.append(src)
                
                caption_div = gallery.find('div', class_='caption')
                name = caption_div.text.strip() if caption_div else 'N/A'
                
                result = {
                    'image_links': list(set(image_links)),
                    'name': name,
                    'code': gallery_code,
                    'tags': data_tags
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error procesando gallery: {e}")
                continue
        
        return results
        
    except Exception as e:
        print(f"Error durante el scraping: {e}")
        return []
    
    finally:
        driver.quit()
        print("Driver cerrado")

def main():
    parser = argparse.ArgumentParser(description='Web scraping de nhentai usando Selenium')
    parser.add_argument('-s', '--search', required=True, help='Termino de busqueda')
    parser.add_argument('-p', '--page', type=int, default=1, help='Numero de pagina (default: 1)')
    
    args = parser.parse_args()
    
    print("Iniciando scraping con Selenium...")
    print(f"Busqueda: {args.search}")
    print(f"Pagina: {args.page}")
    print("-" * 50)
    
    results = scrape_nhentai_with_selenium(args.search, args.page)
    
    if results:
        print(f"Resultados obtenidos: {len(results)}")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"Resultado {i}:")
            print(f"   Codigo: {result['code']}")
            print(f"   Nombre: {result['name']}")
            print(f"   Links de imagenes: {result['image_links']}")
            print(f"   Tags: {len(result['tags'])} tags encontrados")
            print("-" * 40)
    else:
        print("No se obtuvieron resultados")

if __name__ == "__main__":
    main()
                                 
