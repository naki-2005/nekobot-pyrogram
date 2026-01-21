import random
import time
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re

def scrape_nhentai(gallery_number):
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
    chrome_options.add_argument('--accept-language=en-US,en;q=0.9')
    chrome_options.add_argument('--sec-ch-ua="Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"')
    chrome_options.add_argument('--sec-ch-ua-mobile=?0')
    chrome_options.add_argument('--sec-ch-ua-platform="Windows"')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    chrome_binary_path = "selenium/chrome-linux64/chrome"
    chromedriver_path = "selenium/chromedriver-linux64/chromedriver"
    chrome_options.binary_location = chrome_binary_path

    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        url = f"https://nhentai.net/g/{gallery_number}/"
        print(f"🌐 Accediendo a: {url}")
        
        driver.get(url)
        
        max_attempts = 3
        for attempt in range(max_attempts):
            time.sleep(3 + attempt * 2)
            
            page_source = driver.page_source
            if "Just a moment" in page_source or "Verifying you are human" in page_source:
                print(f"⚠️  Cloudflare detectado (intento {attempt + 1}/{max_attempts}), esperando más...")
                time.sleep(5)
                continue
            
            if "gallery" in page_source.lower() or "cover" in page_source.lower():
                break
        
        html_content = driver.page_source
        
        if not html_content or len(html_content) < 100:
            raise Exception("El contenido HTML parece estar vacío o es muy corto")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        title_element = soup.find('h1', class_='title')
        if title_element:
            title_parts = []
            for span in title_element.find_all('span', class_=True):
                title_parts.append(span.get_text(strip=True))
            full_title = ' '.join(title_parts)
        else:
            full_title = "Título no encontrado"
        
        tags_dict = {}
        tags_section = soup.find('section', id='tags')
        if tags_section:
            for tag_container in tags_section.find_all('div', class_='tag-container'):
                field_name = tag_container.get_text(strip=True).split(':')[0].strip()
                tags = []
                for tag_link in tag_container.find_all('a', class_='tag'):
                    tag_name = tag_link.find('span', class_='name')
                    if tag_name:
                        tags.append(tag_name.get_text(strip=True))
                if tags:
                    tags_dict[field_name] = tags
        
        gallery_id = None
        image_links = []
        pattern = re.compile(r'//t[1249]\.nhentai\.net/galleries/(\d+)/(\d+)t\.(webp|jpg|png)')
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src', '')
            if src:
                match = pattern.search(src)
                if match:
                    gallery_id = match.group(1)
                    break
        
        if gallery_id:
            print(f"🔍 ID real de la galería encontrado: {gallery_id}")
            
            total_pages_from_tags = 0
            if 'Pages' in tags_dict and tags_dict['Pages']:
                try:
                    total_pages_from_tags = int(tags_dict['Pages'][0])
                except (ValueError, IndexError):
                    pass
            
            found_thumbnails = []
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src', '')
                if src:
                    match = pattern.search(src)
                    if match:
                        page_num = match.group(2)
                        ext = match.group(3)
                        found_thumbnails.append({
                            'page_num': int(page_num),
                            'ext': ext
                        })
            
            found_thumbnails.sort(key=lambda x: x['page_num'])
            
            if total_pages_from_tags == 0 and found_thumbnails:
                total_pages_from_tags = found_thumbnails[-1]['page_num']
            
            print(f"📊 Páginas en tags: {total_pages_from_tags}, Miniaturas encontradas: {len(found_thumbnails)}")
            
            if total_pages_from_tags > 0:
                extensions_count = {}
                for thumb in found_thumbnails:
                    ext = thumb['ext']
                    extensions_count[ext] = extensions_count.get(ext, 0) + 1
                
                default_ext = 'jpg'
                if extensions_count:
                    default_ext = max(extensions_count.items(), key=lambda x: x[1])[0]
                
                page_ext_map = {thumb['page_num']: thumb['ext'] for thumb in found_thumbnails}
                
                for page_num in range(1, total_pages_from_tags + 1):
                    ext = page_ext_map.get(page_num, default_ext)
                    image_link = f"https://i2.nhentai.net/galleries/{gallery_id}/{page_num}.{ext}"
                    image_links.append(image_link)
                
                print(f"✅ Lista de imágenes autocompletada: {len(image_links)} páginas")
            else:
                for thumb in found_thumbnails:
                    image_link = f"https://i2.nhentai.net/galleries/{gallery_id}/{thumb['page_num']}.{thumb['ext']}"
                    image_links.append(image_link)
                print(f"⚠️  Usando solo miniaturas encontradas: {len(image_links)} páginas")
            
        else:
            print("❌ No se pudo encontrar el ID real de la galería")
            return {"title": full_title, "links": [], "tags": tags_dict}
        
        return {"title": full_title, "links": image_links, "tags": tags_dict}
        
    except Exception as e:
        print(f"❌ Error durante el scraping: {str(e)}")
        return {"title": None, "links": [], "tags": {}}
        
    finally:
        try:
            driver.quit()
            print("🚪 Driver cerrado correctamente")
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description='Scraping de nhentai.net')
    parser.add_argument('-C', '--code', type=int, required=True, 
                       help='Número de la galería de nhentai (ej: 594765)')
    
    args = parser.parse_args()
    
    print(f"🎯 Iniciando scraping para galería: {args.code}")
    print("⏳ Esto puede tomar unos segundos...")
    
    result = scrape_nhentai(args.code)
    
    if result["title"] and result["links"]:
        print("\n" + "="*60)
        print("📖 TÍTULO:")
        print(result["title"])
        
        print("\n🏷️  TAGS:")
        for category, tag_list in result["tags"].items():
            print(f"{category}: {', '.join(tag_list)}")
        
        print(f"\n🔗 LINKS DE IMÁGENES HD ({len(result['links'])} páginas):")
        for i, link in enumerate(result["links"][:5], 1):
            print(f"{i}. {link}")
        if len(result["links"]) > 5:
            print(f"... y {len(result['links']) - 5} más")
        print("="*60)
    else:
        print("❌ No se pudo obtener la información de la galería")

if __name__ == "__main__":
    main()
