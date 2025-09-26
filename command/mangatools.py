import os
import asyncio
import cloudscraper
import concurrent.futures
import zipfile
import tempfile
import shutil
import re
import time
from urllib.parse import urlparse, urljoin, quote_plus
from bs4 import BeautifulSoup
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import BadRequest

user_data = {}
manga_cache = {}
chapters_cache = {}
CACHE_DURATION = 86400 * 7  # 7 días

def cleanup_cache():
    current_time = time.time()
    expired_users = []
    for user_id, cache_data in chapters_cache.items():
        if current_time - cache_data.get('timestamp', 0) > CACHE_DURATION:
            expired_users.append(user_id)
    
    for user_id in expired_users:
        del chapters_cache[user_id]

def save_to_vault(manga_name, chapter_name, cbz_file):
    vault_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vault_files', 'mangas')
    manga_folder = os.path.join(vault_path, manga_name)
    os.makedirs(manga_folder, exist_ok=True)
    
    chapter_file = os.path.join(manga_folder, f"{chapter_name}.cbz")
    shutil.copy2(cbz_file, chapter_file)
    return chapter_file

async def download_full_manga(user_id, chapters, chapter_urls, language, manga_name, save_to_vault=False):
    manga_client = MangaClient(language)
    downloaded_files = []
    
    total_chapters = len(chapters)
    progress_msg = None
    
    for i, (chapter_name, chapter_url) in enumerate(zip(chapters, chapter_urls)):
        if progress_msg is None:
            progress_msg = await manga_client.app.send_message(
                user_id, 
                f"📥 Descargando {manga_name}...\nProgreso: 0/{total_chapters} (0%)"
            )
        
        cbz_file = await download_chapter(chapter_url, chapter_name, manga_client)
        if cbz_file:
            if save_to_vault:
                vault_file = save_to_vault(manga_name, chapter_name, cbz_file)
                downloaded_files.append(vault_file)
            else:
                downloaded_files.append(cbz_file)
            
            progress = i + 1
            percentage = (progress / total_chapters) * 100
            try:
                await progress_msg.edit_text(
                    f"📥 Descargando {manga_name}...\nProgreso: {progress}/{total_chapters} ({percentage:.1f}%)"
                )
            except:
                pass
    
    manga_client.close()
    
    if progress_msg:
        await progress_msg.delete()
    
    return downloaded_files

async def handle_manga_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    cleanup_cache()
    
    if data.startswith("manga_lang_"):
        language = data.split("_")[2]
        
        if user_id not in user_data or "query" not in user_data[user_id]:
            await callback_query.answer("La sesión ha expirado. Por favor, realiza una nueva búsqueda.")
            return
        
        query = user_data[user_id]["query"]
        
        await callback_query.answer("Buscando mangas...")
        
        manga_client = MangaClient(language)
        
        mangas, manga_urls, _ = manga_client.search(query)
        manga_client.close()
        
        if not mangas:
            await callback_query.message.edit_text("No se encontraron mangas con ese nombre.")
            return
        
        user_data[user_id] = {
            "manga_list": mangas,
            "manga_urls": manga_urls,
            "current_page": 0,
            "language": language,
            "query": query
        }
        
        total_mangas = len(mangas)
        current_page = 0
        start_idx = current_page * 10
        end_idx = min(start_idx + 10, total_mangas)
        
        keyboard = []
        for i in range(start_idx, end_idx):
            keyboard.append([InlineKeyboardButton(mangas[i], callback_data=f"manga_{i}")])
        
        nav_buttons = []
        if total_mangas > 10:
            if current_page > 0:
                nav_buttons.append(InlineKeyboardButton("⏪", callback_data="manga_first_page"))
                nav_buttons.append(InlineKeyboardButton("◀️", callback_data="manga_prev_page"))
            
            if end_idx < total_mangas:
                nav_buttons.append(InlineKeyboardButton("▶️", callback_data="manga_next_page"))
                nav_buttons.append(InlineKeyboardButton("⏩", callback_data="manga_last_page"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await callback_query.message.edit_text(
            f"Resultados de búsqueda para '{query}' ({'Español' if language == 'es' else 'Inglés'}):\nMostrando {start_idx + 1}-{end_idx} de {total_mangas}",
            reply_markup=reply_markup
        )
        await callback_query.answer()
    
    elif data in ["manga_first_page", "manga_prev_page", "manga_next_page", "manga_last_page"]:
        if user_id not in user_data or "manga_list" not in user_data[user_id]:
            await callback_query.answer("La sesión ha expirado. Por favor, realiza una nueva búsqueda.")
            return
        
        manga_list = user_data[user_id]["manga_list"]
        current_page = user_data[user_id]["current_page"]
        language = user_data[user_id].get("language", "es")
        query = user_data[user_id].get("query", "")
        
        total_mangas = len(manga_list)
        total_pages = (total_mangas + 9) // 10
        
        if data == "manga_first_page":
            new_page = 0
        elif data == "manga_prev_page":
            new_page = max(0, current_page - 1)
        elif data == "manga_next_page":
            new_page = min(total_pages - 1, current_page + 1)
        elif data == "manga_last_page":
            new_page = total_pages - 1
        
        user_data[user_id]["current_page"] = new_page
        
        start_idx = new_page * 10
        end_idx = min(start_idx + 10, total_mangas)
        
        keyboard = []
        for i in range(start_idx, end_idx):
            keyboard.append([InlineKeyboardButton(manga_list[i], callback_data=f"manga_{i}")])
        
        nav_buttons = []
        if total_mangas > 10:
            if new_page > 0:
                nav_buttons.append(InlineKeyboardButton("⏪", callback_data="manga_first_page"))
                nav_buttons.append(InlineKeyboardButton("◀️", callback_data="manga_prev_page"))
            
            if end_idx < total_mangas:
                nav_buttons.append(InlineKeyboardButton("▶️", callback_data="manga_next_page"))
                nav_buttons.append(InlineKeyboardButton("⏩", callback_data="manga_last_page"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await callback_query.message.edit_text(
            f"Resultados de búsqueda para '{query}' ({'Español' if language == 'es' else 'Inglés'}):\nMostrando {start_idx + 1}-{end_idx} de {total_mangas}",
            reply_markup=reply_markup
        )
        await callback_query.answer()
    
    elif data.startswith("manga_"):
        try:
            manga_index = int(data.split("_")[1])
        except:
            manga_index = -1
        
        if manga_index == -1 or user_id not in user_data or "manga_list" not in user_data[user_id]:
            await callback_query.answer("Manga no válido.")
            return
        
        manga_list = user_data[user_id]["manga_list"]
        manga_urls = user_data[user_id]["manga_urls"]
        language = user_data[user_id].get("language", "es")
        
        if manga_index >= len(manga_list):
            await callback_query.answer("Manga no válido.")
            return
        
        manga_name = manga_list[manga_index]
        manga_url = manga_urls[manga_index]
        
        await callback_query.answer("Cargando capítulos...")
        
        manga_client = MangaClient(language)
        chapters, chapter_urls = manga_client.get_chapters(manga_url)
        manga_client.close()
        
        if not chapters:
            await callback_query.answer("No se encontraron capítulos para este manga.")
            return
        
        chapters_cache[user_id] = {
            "chapters": chapters,
            "chapter_urls": chapter_urls,
            "current_page": 0,
            "manga_name": manga_name,
            "language": language,
            "timestamp": time.time()
        }
        
        total_chapters = len(chapters)
        current_page = 0
        start_idx = current_page * 10
        end_idx = min(start_idx + 10, total_chapters)
        
        keyboard = []
        for i in range(start_idx, end_idx):
            keyboard.append([InlineKeyboardButton(chapters[i], callback_data=f"chapter_{i}")])
        
        nav_buttons = []
        if total_chapters > 10:
            if current_page > 0:
                nav_buttons.append(InlineKeyboardButton("⏪", callback_data="first_page"))
                nav_buttons.append(InlineKeyboardButton("◀️", callback_data="prev_page"))
            
            if end_idx < total_chapters:
                nav_buttons.append(InlineKeyboardButton("▶️", callback_data="next_page"))
                nav_buttons.append(InlineKeyboardButton("⏩", callback_data="last_page"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        action_buttons = [
            InlineKeyboardButton("📥 Descargar Todos", callback_data="chapter_all"),
            InlineKeyboardButton("📁 Guardar Todos", callback_data="save_all")
        ]
        keyboard.append(action_buttons)
        
        manga_buttons = [
            InlineKeyboardButton("📥 Descargar Manga", callback_data="download_manga"),
            InlineKeyboardButton("📁 Guardar Manga", callback_data="save_manga")
        ]
        keyboard.append(manga_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await callback_query.message.edit_text(
            f"Capítulos de {manga_name}:\nMostrando {start_idx + 1}-{end_idx} de {total_chapters}",
            reply_markup=reply_markup
        )
        await callback_query.answer()
    
    elif data in ["first_page", "prev_page", "next_page", "last_page"]:
        if user_id not in chapters_cache:
            await callback_query.answer("La sesión ha expirado. Por favor, realiza una nueva búsqueda.")
            return
        
        cache_data = chapters_cache[user_id]
        chapters = cache_data["chapters"]
        current_page = cache_data["current_page"]
        manga_name = cache_data["manga_name"]
        
        total_chapters = len(chapters)
        total_pages = (total_chapters + 9) // 10
        
        if data == "first_page":
            new_page = 0
        elif data == "prev_page":
            new_page = max(0, current_page - 1)
        elif data == "next_page":
            new_page = min(total_pages - 1, current_page + 1)
        elif data == "last_page":
            new_page = total_pages - 1
        
        chapters_cache[user_id]["current_page"] = new_page
        
        start_idx = new_page * 10
        end_idx = min(start_idx + 10, total_chapters)
        
        keyboard = []
        for i in range(start_idx, end_idx):
            keyboard.append([InlineKeyboardButton(chapters[i], callback_data=f"chapter_{i}")])
        
        nav_buttons = []
        if total_chapters > 10:
            if new_page > 0:
                nav_buttons.append(InlineKeyboardButton("⏪", callback_data="first_page"))
                nav_buttons.append(InlineKeyboardButton("◀️", callback_data="prev_page"))
            
            if end_idx < total_chapters:
                nav_buttons.append(InlineKeyboardButton("▶️", callback_data="next_page"))
                nav_buttons.append(InlineKeyboardButton("⏩", callback_data="last_page"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        action_buttons = [
            InlineKeyboardButton("📥 Descargar Todos", callback_data="chapter_all"),
            InlineKeyboardButton("📁 Guardar Todos", callback_data="save_all")
        ]
        keyboard.append(action_buttons)
        
        manga_buttons = [
            InlineKeyboardButton("📥 Descargar Manga", callback_data="download_manga"),
            InlineKeyboardButton("📁 Guardar Manga", callback_data="save_manga")
        ]
        keyboard.append(manga_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await callback_query.message.edit_text(
            f"Capítulos de {manga_name}:\nMostrando {start_idx + 1}-{end_idx} de {total_chapters}",
            reply_markup=reply_markup
        )
        await callback_query.answer()
    
    elif data == "save_all":
        if user_id not in chapters_cache:
            await callback_query.answer("La sesión ha expirado. Por favor, realiza una nueva búsqueda.")
            return
        
        cache_data = chapters_cache[user_id]
        chapters = cache_data["chapters"]
        chapter_urls = cache_data["chapter_urls"]
        manga_name = cache_data["manga_name"]
        language = cache_data["language"]
        current_page = cache_data["current_page"]
        
        start_idx = current_page * 10
        end_idx = min(start_idx + 10, len(chapters))
        chapters_to_save = end_idx - start_idx
        
        await callback_query.answer(f"Guardando {chapters_to_save} capítulos en vault...")
        
        progress_msg = await callback_query.message.reply(f"📁 Guardando {chapters_to_save} capítulos en vault...")
        
        manga_client = MangaClient(language)
        saved_files = []
        
        for i in range(start_idx, end_idx):
            chapter_name = chapters[i]
            chapter_url = chapter_urls[i]
            
            cbz_file = await download_chapter(chapter_url, chapter_name, manga_client)
            if cbz_file:
                vault_file = save_to_vault(manga_name, chapter_name, cbz_file)
                saved_files.append(vault_file)
                os.remove(cbz_file)
            
            progress = i - start_idx + 1
            await progress_msg.edit_text(f"📁 Guardando... {progress}/{chapters_to_save}")
        
        manga_client.close()
        await progress_msg.edit_text(f"✅ Guardado completado. {len(saved_files)} capítulos guardados en vault.")
    
    elif data == "download_manga":
        if user_id not in chapters_cache:
            await callback_query.answer("La sesión ha expirado. Por favor, realiza una nueva búsqueda.")
            return
        
        cache_data = chapters_cache[user_id]
        chapters = cache_data["chapters"]
        chapter_urls = cache_data["chapter_urls"]
        manga_name = cache_data["manga_name"]
        language = cache_data["language"]
        
        total_chapters = len(chapters)
        await callback_query.answer(f"Descargando {total_chapters} capítulos...")
        
        downloaded_files = await download_full_manga(user_id, chapters, chapter_urls, language, manga_name, False)
        
        if not downloaded_files:
            await callback_query.message.reply("Error al descargar el manga completo.")
            return
        
        progress_msg = await callback_query.message.reply(f"✅ Descarga completada. Enviando {len(downloaded_files)} archivos...")
        
        success_count = 0
        for cbz_file in downloaded_files:
            try:
                await callback_query.message.reply_document(
                    document=cbz_file,
                    caption=f"{manga_name} ({success_count + 1}/{len(downloaded_files)})"
                )
                success_count += 1
                os.remove(cbz_file)
            except Exception as e:
                await callback_query.message.reply(f"Error al enviar archivo: {str(e)}")
        
        await progress_msg.edit_text(f"✅ Proceso completado. {success_count} capítulos enviados.")
    
    elif data == "save_manga":
        if user_id not in chapters_cache:
            await callback_query.answer("La sesión ha expirado. Por favor, realiza una nueva búsqueda.")
            return
        
        cache_data = chapters_cache[user_id]
        chapters = cache_data["chapters"]
        chapter_urls = cache_data["chapter_urls"]
        manga_name = cache_data["manga_name"]
        language = cache_data["language"]
        
        total_chapters = len(chapters)
        await callback_query.answer(f"Guardando {total_chapters} capítulos en vault...")
        
        saved_files = await download_full_manga(user_id, chapters, chapter_urls, language, manga_name, True)
        
        if saved_files:
            await callback_query.message.reply(f"✅ Manga guardado completo. {len(saved_files)} capítulos guardados en vault.")
        else:
            await callback_query.message.reply("❌ Error al guardar el manga completo.")
    
    elif data == "chapter_all":
        if user_id not in chapters_cache:
            await callback_query.answer("La sesión ha expirado. Por favor, realiza una nueva búsqueda.")
            return
        
        cache_data = chapters_cache[user_id]
        chapters = cache_data["chapters"]
        chapter_urls = cache_data["chapter_urls"]
        manga_name = cache_data["manga_name"]
        language = cache_data["language"]
        current_page = cache_data["current_page"]
        
        start_idx = current_page * 10
        end_idx = min(start_idx + 10, len(chapters))
        chapters_to_download = end_idx - start_idx
        
        await callback_query.answer(f"Descargando {chapters_to_download} capítulos...")
        
        progress_msg = await callback_query.message.reply(f"📥 Descargando {chapters_to_download} capítulos...")
        
        manga_client = MangaClient(language)
        downloaded_files = []
        
        for i in range(start_idx, end_idx):
            chapter_name = chapters[i]
            chapter_url = chapter_urls[i]
            
            cbz_file = await download_chapter(chapter_url, chapter_name, manga_client)
            if cbz_file:
                downloaded_files.append(cbz_file)
            
            progress = i - start_idx + 1
            await progress_msg.edit_text(f"📥 Descargando... {progress}/{chapters_to_download}")
        
        manga_client.close()
        
        if not downloaded_files:
            await progress_msg.edit_text("Error al descargar los capítulos.")
            return
        
        await progress_msg.edit_text(f"✅ Descarga completada. Enviando {len(downloaded_files)} archivos...")
        
        success_count = 0
        for cbz_file in downloaded_files:
            try:
                await callback_query.message.reply_document(
                    document=cbz_file,
                    caption=f"¡Capítulo descargado! ({success_count + 1}/{len(downloaded_files)})"
                )
                success_count += 1
                os.remove(cbz_file)
            except Exception as e:
                await callback_query.message.reply(f"Error al enviar archivo: {str(e)}")
        
        await progress_msg.edit_text(f"✅ Proceso completado. {success_count} capítulos enviados.")
    
    elif data.startswith("chapter_"):
        try:
            chapter_index = int(data.split("_")[1])
        except:
            chapter_index = -1
        
        if chapter_index == -1 or user_id not in chapters_cache:
            await callback_query.answer("La sesión ha expirado. Por favor, realiza una nueva búsqueda.")
            return
        
        cache_data = chapters_cache[user_id]
        chapters = cache_data["chapters"]
        chapter_urls = cache_data["chapter_urls"]
        language = cache_data["language"]
        
        if chapter_index >= len(chapters):
            await callback_query.answer("Capítulo no válido.")
            return
        
        chapter_name = chapters[chapter_index]
        chapter_url = chapter_urls[chapter_index]
        
        await callback_query.answer(f"Descargando {chapter_name}...")
        
        manga_client = MangaClient(language)
        cbz_file = await download_chapter(chapter_url, chapter_name, manga_client)
        manga_client.close()
        
        if not cbz_file:
            await callback_query.message.reply(f"Error al descargar el capítulo: {chapter_name}")
            return
        
        try:
            await callback_query.message.reply_document(
                document=cbz_file,
                caption=f"¡Aquí tienes {chapter_name}!"
            )
        except Exception as e:
            await callback_query.message.reply(f"Error al enviar el archivo: {str(e)}")
        
        try:
            os.remove(cbz_file)
        except:
            pass

async def handle_manga_search(client: Client, message: Message, textori: str):
    user_id = message.from_user.id
    parts = textori.split(maxsplit=1)
    
    if len(parts) < 2:
        await message.reply("Por favor, proporciona un nombre de manga o URL. Ejemplo: /manga One Piece o /manga https://es.ninemanga.com/manga/Kuro.html")
        return
    
    query = parts[1].strip()
    
    if re.match(r'https?://(es\.)?ninemanga\.com/manga/', query):
        if 'es.ninemanga.com' in query:
            language = 'es'
        else:
            language = 'en'
        
        manga_client = MangaClient(language)
        manga_name = manga_client.get_manga_name_from_url(query)
        manga_client.close()
        
        if not manga_name:
            await message.reply("No se pudo obtener información del manga desde la URL proporcionada.")
            return
        
        await message.reply(f"🔄 Obteniendo capítulos de {manga_name}...")
        
        manga_client = MangaClient(language)
        chapters, chapter_urls = manga_client.get_chapters(query)
        manga_client.close()
        
        if not chapters:
            await message.reply("No se encontraron capítulos para este manga.")
            return
        
        chapters_cache[user_id] = {
            "chapters": chapters,
            "chapter_urls": chapter_urls,
            "current_page": 0,
            "manga_name": manga_name,
            "language": language,
            "timestamp": time.time()
        }
        
        total_chapters = len(chapters)
        current_page = 0
        start_idx = current_page * 10
        end_idx = min(start_idx + 10, total_chapters)
        
        keyboard = []
        for i in range(start_idx, end_idx):
            keyboard.append([InlineKeyboardButton(chapters[i], callback_data=f"chapter_{i}")])
        
        if total_chapters > 10:
            nav_buttons = []
            if current_page > 0:
                nav_buttons.append(InlineKeyboardButton("⏪", callback_data="first_page"))
                nav_buttons.append(InlineKeyboardButton("◀️", callback_data="prev_page"))
            
            if end_idx < total_chapters:
                nav_buttons.append(InlineKeyboardButton("▶️", callback_data="next_page"))
                nav_buttons.append(InlineKeyboardButton("⏩", callback_data="last_page"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        action_buttons = [
            InlineKeyboardButton("📥 Descargar Todos", callback_data="chapter_all"),
            InlineKeyboardButton("📁 Guardar Todos", callback_data="save_all")
        ]
        keyboard.append(action_buttons)
        
        manga_buttons = [
            InlineKeyboardButton("📥 Descargar Manga", callback_data="download_manga"),
            InlineKeyboardButton("📁 Guardar Manga", callback_data="save_manga")
        ]
        keyboard.append(manga_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply(
            f"📚 Capítulos de {manga_name}:\nMostrando {start_idx + 1}-{end_idx} de {total_chapters}",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🇪🇸 Español", callback_data="manga_lang_es")],
            [InlineKeyboardButton("🇺🇸 Inglés", callback_data="manga_lang_en")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply(
            "Elija el idioma a buscar",
            reply_markup=reply_markup
        )
        
        user_data[user_id] = {"query": query}

def download_image(url, folder, idx, semaphore):
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
        'Referer': 'https://es.ninemanga.com/'
    }
    
    with semaphore:
        scraper = cloudscraper.create_scraper()
        try:
            response = scraper.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            file_path = os.path.join(folder, f'{idx + 1}.jpg')
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            return False

async def download_chapter(chapter_url, chapter_name, client):
    chapter_name = "".join(c for c in chapter_name if c.isalnum() or c in (' ', '.', '_')).rstrip()
    images = client.pictures_from_chapter(chapter_url)
    if not images:
        return None

    folder = tempfile.mkdtemp()
    
    semaphore = asyncio.Semaphore(1)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        futures = []
        for idx, img in enumerate(images):
            futures.append(executor.submit(download_image, img, folder, idx, semaphore))
        
        for future in concurrent.futures.as_completed(futures):
            future.result()

    cbz_filename = f'{chapter_name}.cbz'
    try:
        with zipfile.ZipFile(cbz_filename, 'w') as archive:
            for root, _, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive.write(file_path, arcname=os.path.join(chapter_name, file))
    except Exception as e:
        return None
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    return cbz_filename
    
    elif data == "noop":
        await callback_query.answer()
