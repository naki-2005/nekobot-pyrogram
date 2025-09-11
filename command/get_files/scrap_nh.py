import random
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io
from pyrogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    InputMediaPhoto
)

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

    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined}")
    
    return driver

def download_webp_to_png(image_url):
    try:
        servers = ['t1', 't2', 't4', 't9', 't7', 't5']
        for server in servers:
            try:
                modified_url = image_url.replace('//t4.', f'//{server}.')
                response = requests.get(f"https:{modified_url}", timeout=10)
                if response.status_code == 200:
                    break
            except:
                continue
        
        if response.status_code != 200:
            return None

        image = Image.open(io.BytesIO(response.content))
        png_buffer = io.BytesIO()
        image.save(png_buffer, format='PNG')
        png_buffer.seek(0)
        
        return png_buffer
    except Exception as e:
        print(f"Error descargando imagen: {e}")
        return None

def scrape_nhentai_search(query, page=1):
    """Realiza scraping de búsqueda en nHentai"""
    driver = None
    try:
        driver = setup_driver()
        url = f"https://nhentai.net/search/?q={query}&page={page}"
        print(f"🌐 Accediendo a: {url}")
        
        driver.get(url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "gallery"))
        )
        
        time.sleep(3)
        
        page_source = driver.page_source
        if "Just a moment" in page_source or "Verifying you are human" in page_source:
            print("⚠️ Cloudflare detectado, esperando...")
            time.sleep(10)
        
        doujins = []
        gallery_elements = driver.find_elements(By.CLASS_NAME, "gallery")
        
        for gallery in gallery_elements:
            try:
                link_element = gallery.find_element(By.TAG_NAME, "a")
                href = link_element.get_attribute("href")
                doujin_id = re.search(r'/g/(\d+)/', href)
                if not doujin_id:
                    continue
                
                doujin_id = doujin_id.group(1)
                
                img_element = gallery.find_element(By.TAG_NAME, "img")
                image_url = img_element.get_attribute("data-src") or img_element.get_attribute("src")
                
                caption_element = gallery.find_element(By.CLASS_NAME, "caption")
                title = caption_element.text.strip()
                
                tags_str = gallery.get_attribute("data-tags")
                tags = tags_str.split() if tags_str else []
                
                doujins.append({
                    'id': doujin_id,
                    'title': title,
                    'image_url': image_url,
                    'tags': tags,
                    'url': f"https://nhentai.net/g/{doujin_id}/"
                })
                
            except Exception as e:
                print(f"Error procesando gallery: {e}")
                continue
        
        pagination_info = extract_pagination_info(driver)
        
        return {
            'doujins': doujins,
            'pagination': pagination_info,
            'current_page': page,
            'query': query
        }
        
    except Exception as e:
        print(f"Error en scraping: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def extract_pagination_info(driver):
    """Extrae información de paginación de la página"""
    pagination_info = {
        'pages': [],
        'has_prev': False,
        'has_next': False,
        'total_pages': 1
    }
    
    try:
        pagination_section = driver.find_element(By.CLASS_NAME, "pagination")
        page_elements = pagination_section.find_elements(By.CLASS_NAME, "page")
        
        pages = []
        for page_element in page_elements:
            try:
                page_num = int(page_element.text)
                pages.append(page_num)
            except:
                continue
        
        if pages:
            pagination_info['pages'] = pages
            pagination_info['total_pages'] = max(pages)
            
            next_buttons = pagination_section.find_elements(By.CLASS_NAME, "next")
            prev_buttons = pagination_section.find_elements(By.CLASS_NAME, "prev")
            
            pagination_info['has_next'] = len(next_buttons) > 0
            pagination_info['has_prev'] = len(prev_buttons) > 0
            
    except Exception as e:
        print(f"Error extrayendo paginación: {e}")
    
    return pagination_info

def create_navigation_keyboards(current_index, total_doujins, pagination_info, query, current_page):
    nav_buttons = []
    
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⏪", callback_data=f"nh_first_{current_page}_{query}"))
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"nh_prev_{current_index}_{current_page}_{query}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_doujins}", callback_data="nh_count"))
    
    if current_index < total_doujins - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"nh_next_{current_index}_{current_page}_{query}"))
        nav_buttons.append(InlineKeyboardButton("⏩", callback_data=f"nh_last_{current_page}_{query}"))
    
    page_buttons = []
    pages_to_show = pagination_info['pages'][:8]
    
    for page_num in pages_to_show:
        page_buttons.append(
            InlineKeyboardButton(
                str(page_num), 
                callback_data=f"nh_page_{page_num}_{query}"
            )
        )
    
    download_button = [
        InlineKeyboardButton(
            "📥 Descargar", 
            callback_data=f"nh_dl_{current_index}_{current_page}_{query}"
        )
    ]
    
    keyboards = []
    if nav_buttons:
        keyboards.append(nav_buttons)
    if page_buttons:
        for i in range(0, len(page_buttons), 3):
            keyboards.append(page_buttons[i:i+3])
    if download_button:
        keyboards.append(download_button)
    
    return InlineKeyboardMarkup(keyboards)

async def send_nhentai_results(message, client, query):
    try:
        loading_msg = await message.reply_text("🔍 Buscando en nHentai...")
        
        search_data = scrape_nhentai_search(query)
        if not search_data or not search_data['doujins']:
            await loading_msg.edit_text("❌ No se encontraron resultados o error en el scraping")
            return
        
        doujins = search_data['doujins']
        current_index = 0
        current_doujin = doujins[current_index]
        
        png_buffer = download_webp_to_png(current_doujin['image_url'])
        if not png_buffer:
            await loading_msg.edit_text("❌ Error descargando la imagen")
            return
        
        reply_markup = create_navigation_keyboards(
            current_index, 
            len(doujins), 
            search_data['pagination'],
            query,
            search_data['current_page']
        )
        
        caption = f"**{current_doujin['title']}**\n\n"
        caption += f"📖 ID: `{current_doujin['id']}`\n"
        caption += f"🔗 Descargar con: `/nh {current_doujin['id']}`\n"
        caption += f"📊 Tags: {len(current_doujin['tags'])}"
        
        await loading_msg.delete()
        
        sent_message = await client.send_photo(
            chat_id=message.chat.id,
            photo=png_buffer,
            caption=caption,
            reply_markup=reply_markup
        )
        
        return sent_message
        
    except Exception as e:
        print(f"Error en send_nhentai_results: {e}")
        try:
            await loading_msg.edit_text(f"❌ Error: {str(e)}")
        except:
            await message.reply_text(f"❌ Error: {str(e)}")

async def handle_nhentai_callback(callback_query, client, action, data):
    """Maneja los callbacks de navegación"""
    try:
        await callback_query.answer("Cargando...")
        
        parts = data.split('_')
        
        if action == 'page':
            page_num = int(parts[0])
            query = '_'.join(parts[1:])
            
            await callback_query.message.edit_text("🔍 Cargando nueva página...")
            await handle_page_change(callback_query, client, page_num, query)
            
        elif action == 'next':
            current_index = int(parts[0])
            current_page = int(parts[1])
            query = '_'.join(parts[2:])
            await handle_doujin_navigation(callback_query, client, current_index + 1, current_page, query)
            
        elif action == 'prev':
            current_index = int(parts[0])
            current_page = int(parts[1])
            query = '_'.join(parts[2:])
            await handle_doujin_navigation(callback_query, client, current_index - 1, current_page, query)
            
        elif action == 'first':
            current_page = int(parts[0])
            query = '_'.join(parts[1:])
            await handle_doujin_navigation(callback_query, client, 0, current_page, query)
            
        elif action == 'last':
            current_page = int(parts[0])
            query = '_'.join(parts[1:])
            await callback_query.message.edit_text("🔄 Cargando último resultado...")
            
        elif action == 'dl':
            current_index = int(parts[0])
            current_page = int(parts[1])
            query = '_'.join(parts[2:])
            await callback_query.message.edit_text("📥 Preparando descarga...")
            
    except Exception as e:
        print(f"Error en callback: {e}")
        await callback_query.answer("❌ Error procesando la solicitud")

async def handle_page_change(callback_query, client, page_num, query):
    """Maneja el cambio de página"""
    loading_msg = await callback_query.message.edit_text("🔍 Cargando nueva página...")
    
    search_data = scrape_nhentai_search(query, page_num)
    if not search_data:
        await loading_msg.edit_text("❌ Error cargando la página")
        return
    
    doujins = search_data['doujins']
    current_doujin = doujins[0]
    
    png_buffer = download_webp_to_png(current_doujin['image_url'])
    if not png_buffer:
        await loading_msg.edit_text("❌ Error descargando la imagen")
        return
    
    reply_markup = create_navigation_keyboards(
        0, 
        len(doujins), 
        search_data['pagination'],
        query,
        search_data['current_page']
    )
    
    caption = f"**{current_doujin['title']}**\n\n"
    caption += f"📖 ID: `{current_doujin['id']}`\n"
    caption += f"🔗 Descargar con: `/nh {current_doujin['id']}`\n"
    caption += f"📊 Tags: {len(current_doujin['tags'])}"
    caption += f"\n📄 Página: {page_num}"
    
    await callback_query.message.edit_media(
        InputMediaPhoto(media=png_buffer, caption=caption),
        reply_markup=reply_markup
    )

async def handle_doujin_navigation(callback_query, client, new_index, current_page, query):
    
    await callback_query.message.edit_text("🔄 Cargando...")
    
    search_data = scrape_nhentai_search(query, current_page)
    if not search_data or new_index >= len(search_data['doujins']):
        await callback_query.answer("❌ No hay más resultados")
        return
    
    current_doujin = search_data['doujins'][new_index]
    
    png_buffer = download_webp_to_png(current_doujin['image_url'])
    if not png_buffer:
        await callback_query.answer("❌ Error descargando imagen")
        return
    
    reply_markup = create_navigation_keyboards(
        new_index, 
        len(search_data['doujins']), 
        search_data['pagination'],
        query,
        current_page
    )
    
    caption = f"**{current_doujin['title']}**\n\n"
    caption += f"📖 ID: `{current_doujin['id']}`\n"
    caption += f"🔗 Descargar con: `/nh {current_doujin['id']}`\n"
    caption += f"📊 Tags: {len(current_doujin['tags'])}"
    
    await callback_query.message.edit_media(
        InputMediaPhoto(media=png_buffer, caption=caption),
        reply_markup=reply_markup
    )

def parse_callback_data(data):
    """Parsea los datos del callback"""
    if data.startswith('nh_'):
        parts = data[3:].split('_')
        action = parts[0]
        remaining_data = '_'.join(parts[1:]) if len(parts) > 1 else ""
        return action, remaining_data
    return None, None
